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

import simplejson as json
from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings
from django.contrib.auth import login, logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import View

from telescope2.discord import oauth2
from telescope2.discord.bot import Telescope
from telescope2.utils.jwt import validate_token

from .forms import UserCreateForm
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


async def index(req: HttpRequest) -> HttpResponse:
    if not Telescope.is_alive:
        Telescope.run()

    user: User = req.user

    @sync_to_async
    def is_authenticated():
        return user.is_authenticated

    if not await is_authenticated():
        return render(req, 'web/index.html', {'authenticated': False})

    token = await user.fresh_token()
    if not token:
        await sync_to_async(logout)(req)
        return render(req, 'web/index.html', {'authenticated': False})

    return render(req, 'web/index.html', {
        'authenticated': True,
        'access_token': token,
        'username': user.username,
    })


def user_login(req: HttpRequest) -> HttpResponse:
    redirect_uri, token = oauth2.app_auth_url(req)
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

        tokens = await oauth2.exchange_tokens(req, code)
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

        if not user.password:
            user.set_unusable_password()

        user.access_token = access_token
        user.refresh_token = refresh_token
        user.expires_at = expires_at
        user.save()

        login(req, user)
        return redirect(reverse('web.index'))


def invite(req: HttpRequest) -> HttpResponse:
    redirect, token = oauth2.bot_invite_url(req)
    res = redirect(redirect, status=307)
    res.set_cookie('state', token, settings.JWT_DEFAULT_EXP, secure=True, httponly=True, samesite='Lax')
    return res


def authorized(req: HttpRequest) -> HttpResponse:
    return HttpResponse(content=repr(dict(req.GET)))
