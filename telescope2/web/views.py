# views.py
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

from typing import List

import simplejson as json
from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import View
from more_itertools import partition

from telescope2.discord.fetch import (DiscordFetch, DiscordUnauthorized,
                                      PartialGuild, app_auth_url,
                                      bot_invite_url, create_session)
from telescope2.discord.models import Server
from telescope2.utils.http import HTTPNoContent
from telescope2.utils.jwt import validate_token

from .forms import ServerCreateForm, UserCreateForm
from .models import User


def verify_state(req: HttpRequest):
    cookie_token = req.COOKIES.get('state')
    params_token = req.GET.get('state')
    state = validate_token(req, params_token)
    if state == 'valid':
        if cookie_token == params_token:
            return 'valid'
        return 'invalid'
    return state


async def authenticate(req: HttpRequest):
    user: User = req.user

    @sync_to_async
    def is_authenticated():
        return user.is_authenticated

    if not await is_authenticated():
        raise Logout

    token = await user.fresh_token()
    if not token:
        raise Logout

    fetch = DiscordFetch(user_id=user.discord_id)
    await fetch.init_session(access_token=token, refresh_token=user.refresh_token)

    try:
        guilds = await fetch.fetch_user_guilds()
    except DiscordUnauthorized:
        raise Logout
    finally:
        await fetch.close()

    if guilds is None:
        raise Logout

    return token, guilds


async def logout_current_user(req: HttpResponse) -> HttpResponse:
    await sync_to_async(logout)(req)
    return render(req, 'web/index.html', {'authenticated': False})


async def load_servers(req: HttpRequest, guilds: List[PartialGuild]):
    managed_guilds = {g.id: g for g in guilds if g.perms.manage_guild is True}

    @sync_to_async
    def get_servers():
        return [*Server.objects.filter(gid__in=managed_guilds)]

    servers: List[Server] = await get_servers()
    server_ids = {s.gid for s in servers}

    return partition(lambda g: g[1].id in server_ids, managed_guilds.items())


async def index(req: HttpRequest, guild_id: str = None) -> HttpResponse:
    try:
        token, guilds = await authenticate(req)
    except Logout:
        return await logout_current_user(req)

    available, joined = await load_servers(req, guilds)
    available = dict(available)
    joined = dict(joined)
    guilds = {**available, **joined}

    info = {
        'authenticated': True,
        'access_token': token,
        'username': req.user.username,
        'available_guilds': available,
        'joined_guilds': joined,
    }

    if guild_id is None:
        return render(req, 'web/index.html', info)
    guild_id = int(guild_id)
    if guild_id not in guilds:
        return redirect(reverse('web.index'))

    info['current_guild'] = guilds[guild_id]
    info['joined'] = guild_id in joined

    return render(req, 'web/manage.html', info)


def user_login(req: HttpRequest) -> HttpResponse:
    redirect_uri, token = app_auth_url(req)
    res = redirect(redirect_uri)
    res.set_cookie('state', token, settings.JWT_DEFAULT_EXP, secure=True, httponly=True, samesite='Lax')
    return res


def user_logout(req: HttpRequest) -> HttpResponse:
    logout(req)
    return redirect(reverse('web.index'))


def invalid_login(req: HttpRequest, reason: str) -> HttpResponse:
    return render(req, 'web/invalid-login.html', {'login_state': reason}, status=400)


class CreateUserView(View):
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

        return render(req, 'web/postlogin.html', {'form': UserCreateForm(data=tokens)})

    def post(self, req: HttpRequest) -> HttpResponse:
        invalid_data = redirect(reverse('web.login_invalid', kwargs={'reason': 'invalid_payload'}))

        try:
            user_info = json.loads(req.body.decode('utf8'))
        except json.JSONDecodeError:
            return invalid_data

        form = UserCreateForm(data=user_info)
        if not form.is_valid():
            return invalid_data

        (username, discord_id, access_token,
         refresh_token, expires_at) = form.to_tuple()

        try:
            user = User.objects.get(discord_id=discord_id)
            user.username = username
        except User.DoesNotExist:
            user = User(username=username, discord_id=discord_id)
            user.user_permissions.add('manage_servers')

        if not user.password:
            user.set_unusable_password()

        user.access_token = access_token
        user.refresh_token = refresh_token
        user.expires_at = expires_at
        user.save()

        login(req, user)
        return HTTPNoContent()


@login_required
@permission_required(['manage_servers'])
def join(req: HttpRequest, guild_id: str) -> HttpResponse:
    redirect_uri, token = bot_invite_url(req, guild_id)
    res = redirect(redirect_uri, status=307)
    res.set_cookie('state', token, settings.JWT_DEFAULT_EXP, secure=True, httponly=True, samesite='Lax')
    return res


@login_required
@permission_required(['manage_servers'])
def leave(req: HttpRequest, guild_id: str) -> HttpResponse:
    return


class CreateServerProfileView(View):
    @staticmethod
    @login_required
    @permission_required(['manage_servers'])
    def get(req: HttpRequest) -> HttpResponse:
        state = verify_state(req)
        guild_id = req.GET.get('guild_id')
        if state != 'valid' or not guild_id:
            return HttpResponseBadRequest('Bad credentials')
        return render(req, 'web/joined.html', {
            'form': ServerCreateForm(data={'gid': int(guild_id)}),
        })

    @staticmethod
    @login_required
    @permission_required(['manage_servers'])
    def post(req: HttpRequest) -> HttpResponse:
        form = ServerCreateForm(data=req.POST)
        if not form.is_valid():
            return redirect(reverse('web.index'))
        preference = form.save()
        return redirect(reverse('web.manage', kwargs={'guild_id': preference.gid}))


class Logout(Exception):
    pass
