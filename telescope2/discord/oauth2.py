# oauth2.py
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

from __future__ import annotations

from typing import Tuple
from urllib.parse import urlencode, urlunsplit

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpRequest
from django.urls import reverse

from telescope2.utils.jwt import gen_token

from .bot import Telescope

OAUTH2_PROTOCOL = 'http'
OAUTH2_DOMAIN = 'discord.com'
OAUTH2_PATH = '/api/oauth2/authorize'


def oauth_url(req: HttpRequest, scope: str, redirect: str, token=None, **queries):
    site = get_current_site(req)
    redirect = urlunsplit((req.scheme, site.domain, redirect, '', ''))
    token = token or gen_token(req, settings.JWT_DEFAULT_EXP)
    params = {
        'client_id': settings.DISCORD_CLIENT_ID,
        'scope': scope,
        'response_type': 'code',
        'redirect_uri': redirect,
        'state': token,
    }
    query = urlencode(params)
    return urlunsplit((OAUTH2_PROTOCOL, OAUTH2_DOMAIN, OAUTH2_PATH, query, '')), token


def app_auth_url(req: HttpRequest) -> Tuple[str, str]:
    return oauth_url(req, 'identify guilds', reverse('web.logged_in'))


def bot_invite_url(req: HttpRequest) -> Tuple[str, str]:
    return oauth_url(req, 'bot', reverse('web.authorized'), permissions=Telescope.DEFAULT_PERMS.value)
