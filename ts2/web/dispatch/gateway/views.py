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

from typing import Optional

import simplejson as json
from asgiref.sync import async_to_sync
from discord import Forbidden
from discord.ext.commands import Bot
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

from ts2.discord.fetch import (DiscordCache, DiscordFetch, app_auth_url,
                               bot_invite_url, create_session)
from ts2.discord.models import Server
from ts2.discord.threads import get_thread
from ts2.utils.jwt import validate_token

from ...models import User, manage_permissions_required
from ...utils.http import HTTPCreated
from .forms import ServerCreationForm, UserCreationForm


def verify_state(req: HttpRequest, sub=None, aud=None) -> tuple[str, Optional[dict]]:
    cookie_token = req.COOKIES.get('state')
    params_token = req.GET.get('state')
    state, token = validate_token(req, params_token, sub, aud)
    if state == 'valid':
        if cookie_token == params_token:
            return 'valid', token
        return 'invalid', token
    return state, token


def user_login(req: HttpRequest) -> HttpResponse:
    redirect_uri, token = app_auth_url(req, req.GET.get('next'))
    res = redirect(redirect_uri)
    res.set_cookie('state', token, settings.JWT_DEFAULT_EXP, secure=True, httponly=True, samesite='Lax')
    return res


def user_logout(req: HttpRequest) -> HttpResponse:
    if req.user.is_authenticated:
        DiscordCache(req.user.snowflake).invalidate()
    logout(req)
    return redirect(reverse('web:index'))


def invalid_login(req: HttpRequest, reason: str) -> HttpResponse:
    return render(req, 'ts2/gateway/invalid-login.html', {'login_state': reason}, status=400)


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
        if req.GET.get('error') == 'access_denied':
            return redirect('web:index')

        state, claims = verify_state(req)
        if not claims:
            return redirect('web:index')

        handoff = claims.get('redirect', '')
        code = req.GET.get('code')

        if state != 'valid' or not code:
            return render(req, 'ts2/gateway/invalid-login.html', {'login_state': state})

        fetch = DiscordFetch(create_session())
        tokens = await fetch.exchange_tokens(req, code)
        await fetch.close()
        if tokens is None:
            return render(req, 'ts2/gateway/invalid-login.html', {'login_state': 'incorrect_credentials'})

        return render(req, 'ts2/gateway/postlogin.html', {'form': UserCreationForm(data={**tokens, 'handoff': handoff})})

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
         refresh_token, expires_at, *args) = form.to_tuple()

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
@manage_permissions_required
def join(req: HttpRequest) -> HttpResponse:
    guild_id = req.POST.get('guild_id')
    if not guild_id:
        raise SuspiciousOperation('Invalid parameters.')
    try:
        guild_id = int(guild_id)
    except ValueError:
        raise SuspiciousOperation('Invalid parameters.')
    redirect_uri, token = bot_invite_url(req, guild_id)
    res = redirect(redirect_uri, status=307)
    res.set_cookie('state', token, settings.JWT_DEFAULT_EXP, secure=True, httponly=True, samesite='Lax')
    return res


def cleanup_unauthorized_join(guild_id: str):
    thread = get_thread()

    async def leave(bot: Bot):
        try:
            guild = await bot.fetch_guild(int(guild_id))
        except Forbidden:
            return
        await guild.leave()

    thread.run_coroutine(leave(thread.client))

    try:
        Server.objects.get(snowflake=guild_id).delete()
    except Server.DoesNotExist:
        pass


class CreateServerProfileView(View):
    @staticmethod
    @login_required
    @manage_permissions_required
    def get(req: HttpRequest) -> HttpResponse:
        if req.GET.get('error') == 'access_denied':
            return redirect('web:index')

        guild_id = req.GET.get('guild_id')
        state, token = verify_state(req, sub=guild_id, aud=req.user.pk)
        if state != 'valid' or not guild_id:
            cleanup_unauthorized_join(guild_id)
            raise SuspiciousOperation('Bad credentials.')
        return render(req, 'ts2/gateway/joined.html', {
            'form': ServerCreationForm(data={
                'snowflake': int(guild_id),
                'invited_by': req.user,
                'disable': False,
            }),
        })

    @staticmethod
    @login_required
    @manage_permissions_required
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


@login_required
@require_POST
def refresh_servers(req: HttpRequest):
    return redirect(req.POST.get('dest', reverse('web:index')))
