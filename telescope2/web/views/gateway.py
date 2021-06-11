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
from discord import Forbidden, Guild, Member
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission
from django.core.exceptions import SuspiciousOperation
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import View

from telescope2.discord.fetch import (DiscordFetch, app_auth_url,
                                      bot_invite_url, create_session)
from telescope2.discord.models import Server
from telescope2.utils.http import HTTPNoContent
from telescope2.utils.jwt import validate_token

from ..forms import ServerCreationForm, UserCreationForm
from ..models import User, write_access_required


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
    return render(req, 'web/index.html')


def user_login(req: HttpRequest) -> HttpResponse:
    redirect_uri, token = app_auth_url(req)
    res = redirect(redirect_uri)
    res.set_cookie('state', token, settings.JWT_DEFAULT_EXP, secure=True, httponly=True, samesite='Lax')
    return res


def user_logout(req: HttpRequest) -> HttpResponse:
    logout(req)
    return redirect(reverse('web:index'))


def invalid_login(req: HttpRequest, reason: str) -> HttpResponse:
    return render(req, 'web/invalid-login.html', {'login_state': reason}, status=400)


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
            return render(req, 'web/invalid-login.html', {'login_state': state})

        fetch = DiscordFetch(create_session())
        tokens = await fetch.exchange_tokens(req, code)
        await fetch.close()
        if tokens is None:
            return render(req, 'web/invalid-login.html', {'login_state': 'incorrect_credentials'})

        return render(req, 'web/postlogin.html', {'form': UserCreationForm(data=tokens)})

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
        return HTTPNoContent()


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
        return render(req, 'web/joined.html', {
            'form': ServerCreationForm(data={'snowflake': int(guild_id)}),
        })

    @staticmethod
    @login_required
    @write_access_required
    def post(req: HttpRequest) -> HttpResponse:
        form = ServerCreationForm(data=req.POST)
        if not form.is_valid():
            return redirect(reverse('web:index'))
        preference = form.save()
        return redirect(reverse('web:manage.index', kwargs={'guild_id': preference.snowflake}))


class DeleteServerProfileView(View):
    @staticmethod
    @login_required
    @write_access_required
    def get(req: HttpRequest, guild_id: str) -> HttpResponse:
        return render(req, 'web/leave.html')

    @staticmethod
    @login_required
    @write_access_required
    @async_to_sync
    async def post(req: HttpRequest, guild_id: str) -> HttpResponse:
        guild_id = req.POST.get('guild_id')
        try:
            guild_id = int(guild_id)
        except ValueError:
            guild_id = None
        if not guild_id:
            raise SuspiciousOperation('Invalid parameters.')

        fetch = DiscordFetch()
        await fetch.init_bot()

        try:
            guild: Guild = await fetch.bot.fetch_guild(guild_id)
            member: Member = await guild.fetch_member(req.user.snowflake)
        except Forbidden:
            raise SuspiciousOperation('Insufficient permission.')
        if not member:
            raise SuspiciousOperation('Invalid parameters.')
        if not member.guild_permissions.manage_guild:
            raise SuspiciousOperation('Insufficient permission.')

        @sync_to_async
        def delete_server():
            try:
                server: Server = Server.objects.get(snowflake=guild_id)
            except Server.DoesNotExist:
                return
            server.delete()

        await guild.leave()
        await delete_server()
        await fetch.close()

        return redirect(reverse('web:manage.index', kwargs={'guild_id': guild_id}))
