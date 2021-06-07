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

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode, urlunsplit

import aiohttp
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpRequest
from django.urls import reverse

from telescope2.utils.jwt import gen_token

from .bot import Telescope

OAUTH2_PROTOCOL = 'http'
OAUTH2_DOMAIN = 'discord.com'
OAUTH2_PATH = '/api/oauth2/authorize'


def create_session():
    return aiohttp.ClientSession(headers={
        'User-Agent': settings.USER_AGENT,
    })


def complete_endpoint(req: HttpRequest, endpoint: str, params: str = '', hash_: str = ''):
    site = get_current_site(req)
    return urlunsplit((req.scheme, site.domain, endpoint, params, hash_))


def oauth_url(req: HttpRequest, scope: str, redirect: str, token=None, **queries):
    redirect = complete_endpoint(req, redirect)
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
    return oauth_url(req, 'identify guilds', reverse('web.create_user'))


def bot_invite_url(req: HttpRequest) -> Tuple[str, str]:
    return oauth_url(req, 'bot', reverse('web.authorized'), permissions=Telescope.DEFAULT_PERMS.value)


async def request_token(form: aiohttp.FormData):
    async with create_session() as session:
        async with session.post('https://discordapp.com/api/oauth2/token', data=form) as res:
            data = await res.json()
        if 'access_token' in data:
            data['expires_at'] = int((datetime.now(tz=timezone.utc) + timedelta(seconds=data['expires_in'])).timestamp())
            return data
        return None


async def exchange_tokens(req: HttpRequest, code: str) -> Optional[Dict]:
    form = aiohttp.FormData()
    form.add_field('client_id', settings.DISCORD_CLIENT_ID)
    form.add_field('client_secret', settings.DISCORD_CLIENT_SECRET)
    form.add_field('code', code)
    form.add_field('grant_type', 'authorization_code')
    form.add_field('redirect_uri', complete_endpoint(req, reverse('web.create_user')))
    return await request_token(form)


async def refresh_tokens(refresh_token: str) -> Optional[Dict]:
    form = aiohttp.FormData()
    form.add_field('client_id', settings.DISCORD_CLIENT_ID)
    form.add_field('client_secret', settings.DISCORD_CLIENT_SECRET)
    form.add_field('grant_type', 'refresh_token')
    form.add_field('refresh_token', refresh_token)
    return await request_token(form)
