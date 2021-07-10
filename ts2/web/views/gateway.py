# gateway.py
# Copyright (C) 2021  @tonyzbf +https://github.com/tonyzbf/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import simplejson as json
from asgiref.sync import async_to_sync, sync_to_async
from discord import Forbidden, Guild
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import View

from ts2.discord.apps import DiscordBotConfig
from ts2.discord.fetch import (DiscordCache, DiscordFetch, app_auth_url,
                               bot_invite_url, create_session)
from ts2.discord.models import Server

from ..forms import ServerCreationForm, UserCreationForm
from ..models import User, write_access_required
from ..utils.http import HTTPCreated
from ..utils.jwt import validate_token


def verify_state(req: HttpRequest):
    cookie_token = req.COOKIES.get('state')
    params_token = req.GET.get('state')
    state = validate_token(req, params_token)
    if state == 'valid':
        if cookie_token == params_token:
            return 'valid'
        return 'invalid'
    return state


async def index(req: HttpRequest) -> HttpResponse:
    return render(req, 'telescope2/web/index.html')


def user_login(req: HttpRequest) -> HttpResponse:
    redirect_uri, token = app_auth_url(req)
    res = redirect(redirect_uri)
    res.set_cookie('state', token, settings.JWT_DEFAULT_EXP, secure=True, httponly=True, samesite='Lax')
    return res


def user_logout(req: HttpRequest) -> HttpResponse:
    DiscordCache(req.user.snowflake).invalidate()
    logout(req)
    return redirect(reverse('web:index'))


def invalid_login(req: HttpRequest, reason: str) -> HttpResponse:
    return render(req, 'telescope2/web/invalid-login.html', {'login_state': reason}, status=400)


class CreateUserView(View):
    def create_user(self, username, snowflake) -> User:
        user = User(username=username, snowflake=snowflake)
        perms = Permission.objects.filter(
            content_type__app_label=Server._meta.app_label,
            content_type__model=Server._meta.model_name,
        )
        user.save()
        user.user_permissions.add(*perms)
        user.save()
        return user

    @async_to_sync
    async def get(self, req: HttpRequest) -> HttpResponse:
        state = verify_state(req)
        code = req.GET.get('code')

        if state != 'valid' or not code:
            return render(req, 'telescope2/web/invalid-login.html', {'login_state': state})

        fetch = DiscordFetch(create_session())
        tokens = await fetch.exchange_tokens(req, code)
        await fetch.close()
        if tokens is None:
            return render(req, 'telescope2/web/invalid-login.html', {'login_state': 'incorrect_credentials'})

        return render(req, 'telescope2/web/postlogin.html', {'form': UserCreationForm(data=tokens)})

    def post(self, req: HttpRequest) -> HttpResponse:
        invalid_data = redirect(reverse('web:login_invalid', kwargs={'reason': 'invalid_payload'}))

        try:
            user_info = json.loads(req.body.decode('utf8'))
        except json.JSONDecodeError:
            return invalid_data

        form = UserCreationForm(data=user_info)
        if not form.is_valid():
            return invalid_data

        (username, snowflake, access_token,
         refresh_token, expires_at) = form.to_tuple()

        try:
            user = User.objects.get(snowflake=snowflake)
            user.username = username
        except User.DoesNotExist:
            user = self.create_user(username, snowflake)

        if not user.password:
            user.set_unusable_password()

        user.access_token = access_token
        user.refresh_token = refresh_token
        user.expires_at = expires_at
        user.save()

        login(req, user)
        return HTTPCreated()


@require_POST
@login_required
@write_access_required
def join(req: HttpRequest) -> HttpResponse:
    guild_id = req.POST.get('guild_id')
    if not guild_id:
        raise SuspiciousOperation('Invalid parameters.')
    redirect_uri, token = bot_invite_url(req, guild_id)
    res = redirect(redirect_uri, status=307)
    res.set_cookie('state', token, settings.JWT_DEFAULT_EXP, secure=True, httponly=True, samesite='Lax')
    return res


class CreateServerProfileView(View):
    @staticmethod
    @login_required
    @write_access_required
    def get(req: HttpRequest) -> HttpResponse:
        state = verify_state(req)
        guild_id = req.GET.get('guild_id')
        if state != 'valid' or not guild_id:
            raise SuspiciousOperation('Bad credentials.')
        return render(req, 'telescope2/web/joined.html', {
            'form': ServerCreationForm(data={
                'snowflake': int(guild_id),
                'invited_by': req.user,
                'disable': False,
            }),
        })

    @staticmethod
    @login_required
    @write_access_required
    def post(req: HttpRequest) -> HttpResponse:
        try:
            instance = Server.objects.get(pk=req.POST.get('snowflake'))
        except Server.DoesNotExist:
            instance = None
        form = ServerCreationForm(data=req.POST, instance=instance)
        if not form.is_valid():
            try:
                is_race_condition = form.errors['snowflake'].data[0].code == 'unique'
                if not is_race_condition:
                    return redirect(reverse('web:index'))
            except (KeyError, IndexError):
                return redirect(reverse('web:index'))
        try:
            preference = form.save()
            snowflake = preference.snowflake
        except ValueError:
            snowflake = req.POST['snowflake']
        return redirect(reverse('web:manage.index', kwargs={'guild_id': snowflake}))


def user_invited_guild(user: User, guild_id: str) -> bool:
    return user.invited_servers.filter(snowflake__exact=guild_id).exists()


class DeleteServerProfileView(View):
    @staticmethod
    @login_required
    @write_access_required
    def get(req: HttpRequest, guild_id: str) -> HttpResponse:
        if user_invited_guild(req.user, guild_id):
            return render(req, 'telescope2/web/leave.html')
        raise PermissionDenied()

    @staticmethod
    @login_required
    @write_access_required
    @async_to_sync
    async def post(req: HttpRequest, guild_id: str) -> HttpResponse:
        if not user_invited_guild(req.user, guild_id):
            raise PermissionDenied()
        guild_id = req.POST.get('guild_id')
        try:
            guild_id = int(guild_id)
        except ValueError:
            guild_id = None
        if not guild_id:
            raise SuspiciousOperation('Invalid parameters.')

        thread = DiscordBotConfig.get().bot_thread

        async def get(bot):
            guild: Guild = await bot.fetch_guild(guild_id)
            return guild, await guild.fetch_member(req.user.snowflake)

        try:
            result = thread.run_coroutine(get(thread.client))
        except Forbidden:
            raise SuspiciousOperation('Insufficient permission.')

        guild, member = result
        if not member:
            raise SuspiciousOperation('Invalid parameters.')
        if not member.guild_permissions.manage_guild:
            raise SuspiciousOperation('Insufficient permission.')

        @sync_to_async(thread_sensitive=False)
        def delete_server():
            try:
                server: Server = Server.objects.get(snowflake=guild_id)
            except Server.DoesNotExist:
                return
            server.delete()

        async def leave():
            await guild.leave()
            await delete_server()
        thread.run_coroutine(leave())

        return redirect(reverse('web:manage.index', kwargs={'guild_id': guild_id}))


class ResetServerDataView(View):
    @staticmethod
    @login_required
    @write_access_required
    def get(req: HttpRequest, guild_id: str) -> HttpResponse:
        return render(req, 'telescope2/web/reset.html')

    @staticmethod
    @login_required
    @write_access_required
    def post(req: HttpRequest, guild_id: str) -> HttpResponse:
        guild_id = req.POST.get('guild_id')
        try:
            guild_id = int(guild_id)
        except ValueError:
            guild_id = None
        if not guild_id:
            raise SuspiciousOperation('Invalid parameters.')

        ctx = req.discord
        ctx.server.delete()

        return redirect(reverse('web:manage.index', kwargs={'guild_id': guild_id}))
