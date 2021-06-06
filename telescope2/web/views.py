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

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render

from telescope2.discord import oauth2
from telescope2.discord.bot import Telescope
from telescope2.utils.jwt import validate_token


def verify_state(req: HttpRequest):
    cookie_token = req.COOKIES.get('state')
    params_token = req.GET.get('state')
    state = validate_token(req, params_token)
    if state == 'valid':
        if cookie_token == params_token:
            return 'valid'
        return 'invalid'
    return state


def index(req: HttpRequest) -> HttpResponse:
    if not Telescope.is_alive:
        Telescope.run()
    return render(req, 'web/index.html')


def login(req: HttpRequest) -> HttpResponse:
    redirect, token = oauth2.app_auth_url(req)
    res = HttpResponseRedirect(redirect, status=307)
    res.set_cookie('state', token, settings.JWT_DEFAULT_EXP, secure=True, httponly=True, samesite='Lax')
    return res


def logged_in(req: HttpRequest) -> HttpResponse:
    state = verify_state(req)
    if state != 'valid':
        return render(req, 'web/invalid_login.html', context={
            'token_state': state,
        })
    return HttpResponse(content=repr(dict(req.GET)))


def invite(req: HttpRequest) -> HttpResponse:
    redirect, token = oauth2.bot_invite_url(req)
    res = HttpResponseRedirect(redirect, status=307)
    res.set_cookie('state', token, settings.JWT_DEFAULT_EXP, secure=True, httponly=True, samesite='Lax')
    return res


def authorized(req: HttpRequest) -> HttpResponse:
    return HttpResponse(content=repr(dict(req.GET)))
