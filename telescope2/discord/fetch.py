# fetch.py
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

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable, Coroutine, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urlunsplit

import aiohttp
from aiohttp import ClientSession
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.http import HttpRequest
from django.urls import reverse

from discord import Permissions
from telescope2.utils.datetime import utcnow, utctimestamp
from telescope2.utils.jwt import gen_token

from .bot import Telescope

OAUTH2_PROTOCOL = 'https'
OAUTH2_DOMAIN = 'discord.com'
OAUTH2_PATH = '/api/oauth2/authorize'

CDN_PREFIX = 'https://cdn.discordapp.com'


def create_session(loop=None):
    return aiohttp.ClientSession(
        loop=loop,
        headers={
            'User-Agent': settings.USER_AGENT,
        },
    )


def complete_endpoint(req: HttpRequest, endpoint: str, params: str = '', hash_: str = ''):
    site = get_current_site(req)
    return urlunsplit((req.scheme, site.domain, endpoint, params, hash_))


def oauth_url(req: HttpRequest, scope: str, redirect: str, token=None, **queries):
    redirect = complete_endpoint(req, redirect)
    token = token or gen_token(req, settings.JWT_DEFAULT_EXP)
    params = {
        **queries,
        'client_id': settings.DISCORD_CLIENT_ID,
        'scope': scope,
        'response_type': 'code',
        'redirect_uri': redirect,
        'state': token,
    }
    query = urlencode(params)
    return urlunsplit((OAUTH2_PROTOCOL, OAUTH2_DOMAIN, OAUTH2_PATH, query, '')), token


def api_endpoint(endpoint: str) -> str:
    return f'{OAUTH2_PROTOCOL}://{OAUTH2_DOMAIN}/api{endpoint}'


def app_auth_url(req: HttpRequest) -> Tuple[str, str]:
    return oauth_url(req, 'identify guilds', reverse('web.create_user'))


def bot_invite_url(req: HttpRequest, guild_id: str | int) -> Tuple[str, str]:
    return oauth_url(req, 'bot', reverse('web.authorized'), guild_id=guild_id,
                     permissions=Telescope.DEFAULT_PERMS.value, disable_guild_select='true')


class DiscordRateLimiter:
    rate_reset_time: Dict[Tuple[str, str], float] = {}

    def __setitem__(self, route: Tuple[str, str], timestamp: float):
        self.rate_reset_time[route] = timestamp

    @asynccontextmanager
    async def __call__(self, route: Tuple[str, str]):
        now = utctimestamp()
        timeout = self.rate_reset_time.get(route, 0) - now
        try:
            if timeout > 0:
                await asyncio.sleep(timeout)
            self.rate_reset_time[route] = now + 1
            yield
        finally:
            return


class DiscordCache:
    ENDPOINT_TTL = {
        ('GET', api_endpoint('/users/@me/guilds')): 60 * 5,
    }

    def __init__(self, user_id: int):
        self.user_id = user_id

    def _key(self, endpoint):
        method, url = endpoint
        return f'buffer:{self.user_id}:{method}:{url}'

    def __setitem__(self, endpoint: Tuple[str, str], data: Dict):
        if self.user_id == -1:
            return
        key = self._key(endpoint)
        ttl = self.ENDPOINT_TTL.get(endpoint)
        if ttl:
            cache.set(key, data, timeout=ttl)

    def __getitem__(self, endpoint: Tuple[str, str]) -> Optional[Dict]:
        if self.user_id == -1:
            return
        key = self._key(endpoint)
        return cache.get(key)


class DiscordFetch:
    def __init__(self, session: Optional[ClientSession] = None, user_id: int = -1):
        self.log = logging.getLogger('discord.fetch')
        self._session: ClientSession = session
        self._bot: Telescope

        self._access: Optional[str]
        self._refresh: Optional[str]

        self._ratelimit = asyncio.Event()
        self._ratelimit.set()

        self._throttle_route = DiscordRateLimiter()
        self._cache = DiscordCache(user_id)

    @property
    def bot(self) -> Telescope:
        return self._bot

    async def init_session(self, access_token: Optional[str] = None,
                           refresh_token: Optional[str] = None):
        self._access = access_token
        self._refresh = refresh_token
        self._session = self._session or create_session()

    async def init_bot(self):
        loop = asyncio.get_event_loop()
        self._bot = Telescope(loop=loop)
        await self._bot.login(settings.DISCORD_BOT_TOKEN)

    async def request_token(self, form: aiohttp.FormData) -> Optional[Dict]:
        async with self._session.post('https://discordapp.com/api/oauth2/token', data=form) as res:
            data = await res.json()
        if 'access_token' in data:
            data['expires_at'] = int((utcnow() + timedelta(seconds=data['expires_in'])).timestamp())
            return data
        return None

    async def exchange_tokens(self, req: HttpRequest, code: str) -> Optional[Dict]:
        form = aiohttp.FormData()
        form.add_field('client_id', settings.DISCORD_CLIENT_ID)
        form.add_field('client_secret', settings.DISCORD_CLIENT_SECRET)
        form.add_field('code', code)
        form.add_field('grant_type', 'authorization_code')
        form.add_field('redirect_uri', complete_endpoint(req, reverse('web.create_user')))
        return await self.request_token(form)

    async def refresh_tokens(self, refresh_token: str) -> Optional[Dict]:
        form = aiohttp.FormData()
        form.add_field('client_id', settings.DISCORD_CLIENT_ID)
        form.add_field('client_secret', settings.DISCORD_CLIENT_SECRET)
        form.add_field('grant_type', 'refresh_token')
        form.add_field('refresh_token', refresh_token)
        return await self.request_token(form)

    async def _throttle(self, endpoint, res: aiohttp.ClientResponse):
        if res.status == 429:
            await self._wait(20)
            return False
        retry_after = res.headers.get('retry-after')
        if retry_after:
            await self._wait(int(retry_after) + 1)
            return False
        rate_remaining = res.headers.get('x-ratelimit-remaining')
        rate_reset_after = res.headers.get('x-ratelimit-reset')
        if not rate_remaining or not rate_reset_after:
            return True
        rate_remaining = int(rate_remaining)
        rate_reset_after = float(rate_reset_after)
        self._throttle_route[endpoint] = rate_reset_after
        return True

    async def _wait(self, sec: float):
        if not self._ratelimit.is_set():
            return
        if not sec:
            return
        self.log.warning(f'Rate limit hit, pausing for {sec} seconds')
        self._ratelimit.clear()
        await asyncio.sleep(sec)
        self._ratelimit.set()

    async def _request(self, method: str, url: str, retry=5, **options) -> Optional[Dict]:
        cached = self._cache[method, url]
        if cached is not None:
            return cached

        while retry:
            await self._ratelimit.wait()

            async with self._throttle_route((method, url)):

                self.log.info(f'{method} {url}')
                async with self._session.request(method, url, **options) as res:
                    self.log.info(f'Received {url}')

                    if res.status == 401:
                        raise DiscordUnauthorized()
                    if not await self._throttle((method, url), res):
                        self.log.warning(f'Retrying {url}')
                        retry -= 1
                        continue
                    try:
                        data = await res.json()
                        self._cache[method, url] = data
                        return data
                    except Exception:
                        return None

    async def get(self, endpoint: str) -> Optional[Dict]:
        return await self._request('GET', api_endpoint(endpoint), headers={'Authorization': f'Bearer {self._access}'})

    async def autorefresh(self, coro_func: Callable[[], Coroutine]):
        try:
            return await coro_func()
        except DiscordUnauthorized:
            tokens = await self.refresh_tokens(self._refresh)
            if not tokens:
                raise
            self._access = tokens['access_token']
            self._refresh = tokens['refresh_token']
            return await self.autorefresh(coro_func)

    async def fetch_user_guilds(self) -> Optional[List[PartialGuild]]:
        guilds = await self.autorefresh(lambda: self.get('/users/@me/guilds'))
        if guilds is None:
            return None
        return [PartialGuild.from_dict(g) for g in guilds]

    async def close(self):
        if self._session:
            await self._session.close()
        if hasattr(self, '_bot'):
            await self._bot.logout()


class DiscordUnauthorized(Exception):
    pass


@dataclass
class PartialGuild:
    id: int
    name: str
    icon: str
    perms: Optional[Permissions]

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(id=data['id'], name=data['name'],
                   icon=data['icon'], perms=data['permissions'])

    @property
    def icon_url(self) -> str:
        return f'{CDN_PREFIX}/icons/{self.id}/{self.icon}.png'

    def __post_init__(self):
        self.id = int(self.id)
        if self.perms:
            self.perms = Permissions(int(self.perms))
