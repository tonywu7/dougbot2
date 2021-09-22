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
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional
from urllib.parse import urlencode, urlunsplit

import aiohttp
from aiohttp import ClientSession
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.http import HttpRequest
from django.urls import reverse
from duckcord.permissions import Permissions2

from ts2.utils.jwt import gen_token

from .utils.datetime import utcnow, utctimestamp

OAUTH2_PROTOCOL = 'https'
OAUTH2_DOMAIN = 'discord.com'
OAUTH2_PATH = '/api/oauth2/authorize'

CDN_PREFIX = 'https://cdn.discordapp.com'


def create_session(loop=None):
    """Get a new `aiohttp.ClientSession` to be used for fetching Discord info."""
    return aiohttp.ClientSession(loop=loop, headers={'User-Agent': settings.USER_AGENT})


def complete_endpoint(req: HttpRequest, endpoint: str, params: str = '', fragment: str = ''):
    """Return an API/webpage endpoint completed with the current request's protocol and domain.

    :param req: The current request context.
    :type req: HttpRequest
    :param endpoint: Path to the endpoint.
    :type endpoint: str
    :param params: Additional URL parameters, defaults to ''
    :type params: str, optional
    :param fragment: Additional URL fragment, defaults to ''
    :type fragment: str, optional
    """
    site = get_current_site(req)
    return urlunsplit((req.scheme, site.domain, endpoint, params, fragment))


def oauth_url(
    req: HttpRequest, scope: str, redirect: str,
    claims: Optional[dict] = None, **queries,
) -> tuple[str, str]:
    """Create a Discord OAuth2 URL.

    :param req: The current request context.
    :type req: HttpRequest
    :param scope: Discord auth scopes to request as a space-separated string.
    :type scope: str
    :param redirect: URL to redirect the user to after authorization finished.
    :type redirect: str
    :param claims: Additional JWT claims to be included in the `state` parameter, defaults to None
    :type claims: Optional[dict], optional
    :return: The URL and the JWT state as a tuple.
    :rtype: tuple[str, str]
    """
    redirect = complete_endpoint(req, redirect)
    claims = claims or {}
    token = gen_token(req, settings.JWT_DEFAULT_EXP, **claims)
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
    """Return a complete Discord API URL including protocol and domain."""
    return f'{OAUTH2_PROTOCOL}://{OAUTH2_DOMAIN}/api{endpoint}'


def app_auth_url(req: HttpRequest, redirect: Optional[str] = None) -> tuple[str, str]:
    """Create an OAuth2 URL to be used for user creation and single sign-on.

    :param req: The current request context.
    :type req: HttpRequest
    :param redirect: URL to redirect to after login, defaults to None
    :type redirect: Optional[str], optional
    :return: The URL and the JWT state as a tuple.
    :rtype: tuple[str, str]
    """
    if redirect:
        claims = {'redirect': redirect}
    else:
        claims = {}
    return oauth_url(req, 'identify guilds', reverse('web:create_user'), claims)


def bot_invite_url(req: HttpRequest, guild_id: str | int) -> tuple[str, str]:
    """Create an OAuth2 URL to be used for inviting the bot to a guild.

    :param req: The current request context.
    :type req: HttpRequest
    :param guild_id: The guild to invite the bot to.
    :type guild_id: str | int
    :return: The URL and the JWT state as a tuple.
    :rtype: tuple[str, str]
    """
    from .bot import Robot
    claims = {'sub': int(guild_id), 'aud': req.user.pk}
    return oauth_url(req, 'bot', reverse('web:authorized'), claims=claims, guild_id=guild_id,
                     permissions=Robot.DEFAULT_PERMS.value, disable_guild_select='true')


class DiscordRateLimiter:
    """Utility class to store and enforce Discord rate limits.

    Used in `DiscordFetch` to prevent API abuse.
    """

    rate_reset_time: dict[tuple[str, str], float] = {}

    def __setitem__(self, route: tuple[str, str], timestamp: float):
        self.rate_reset_time[route] = timestamp

    @asynccontextmanager
    async def __call__(self, route: tuple[str, str]):
        """Sleep until this route's rate limit is reset if it is currently throttled.

        :param route: HTTP method and path of the API endpoint as a tuple.
        :type route: tuple[str, str]
        """
        # TODO: Rewrite as normal function
        now = utctimestamp()
        timeout = self.rate_reset_time.get(route, 0) - now
        try:
            if timeout > 0:
                await asyncio.sleep(timeout)
            self.rate_reset_time[route] = now + 1
            yield
        finally:
            pass


class DiscordCache:
    """Rudimentary in-memory cache for Discord API responses."""

    ENDPOINT_TTL = {
        ('GET', api_endpoint('/users/@me/guilds')): 60 * 5,
        ('GET', api_endpoint('/users/@me')): 60 * 5,
    }

    def __init__(self, user_id: int):
        self.user_id = user_id

    def _key(self, endpoint):
        method, url = endpoint
        return f'buffer:{self.user_id}:{method}:{url}'

    def __setitem__(self, endpoint: tuple[str, str], data: dict):
        if self.user_id == -1:
            return
        key = self._key(endpoint)
        ttl = self.ENDPOINT_TTL.get(endpoint)
        if ttl:
            cache.set(key, data, timeout=ttl)

    def __getitem__(self, endpoint: tuple[str, str]) -> Optional[dict]:
        if self.user_id == -1:
            return
        key = self._key(endpoint)
        return cache.get(key)

    def invalidate(self):
        """Invalidate all cached responses."""
        for endpoint in self.ENDPOINT_TTL:
            cache.delete(self._key(endpoint))


class DiscordFetch:
    """Simple client for Discord APIs."""

    def __init__(self, session: Optional[ClientSession] = None, user_id: int = -1):
        self.log = logging.getLogger('discord.fetch')
        self._session: ClientSession = session

        self._access: Optional[str]
        self._refresh: Optional[str]

        self._ratelimit = asyncio.Event()
        self._ratelimit.set()

        self._throttle_route = DiscordRateLimiter()
        self._cache = DiscordCache(user_id)

    async def init_session(self, access_token: Optional[str] = None,
                           refresh_token: Optional[str] = None):
        """Initialize an `aiohttp.ClientSession`, optionally with access/refresh tokens."""
        self._access = access_token
        self._refresh = refresh_token
        self._session = self._session or create_session()

    async def request_token(self, form: aiohttp.FormData) -> Optional[dict]:
        """Request an access token from Discord."""
        async with self._session.post('https://discordapp.com/api/oauth2/token', data=form) as res:
            data = await res.json()
        if 'access_token' in data:
            data['expires_at'] = int((utcnow() + timedelta(seconds=data['expires_in'])).timestamp())
            return data
        return None

    async def exchange_tokens(self, req: HttpRequest, code: str) -> Optional[dict]:
        """Exchange an OAuth code grant for an access token."""
        form = aiohttp.FormData()
        form.add_field('client_id', settings.DISCORD_CLIENT_ID)
        form.add_field('client_secret', settings.DISCORD_CLIENT_SECRET)
        form.add_field('code', code)
        form.add_field('grant_type', 'authorization_code')
        form.add_field('redirect_uri', complete_endpoint(req, reverse('web:create_user')))
        return await self.request_token(form)

    async def refresh_tokens(self, refresh_token: str) -> Optional[dict]:
        """Request a new access token using a refresh token."""
        form = aiohttp.FormData()
        form.add_field('client_id', settings.DISCORD_CLIENT_ID)
        form.add_field('client_secret', settings.DISCORD_CLIENT_SECRET)
        form.add_field('grant_type', 'refresh_token')
        form.add_field('refresh_token', refresh_token)
        return await self.request_token(form)

    async def revoke_token(self, refresh_token: str) -> None:
        """Revoke a refresh token."""
        form = aiohttp.FormData()
        form.add_field('client_id', settings.DISCORD_CLIENT_ID)
        form.add_field('client_secret', settings.DISCORD_CLIENT_SECRET)
        form.add_field('token', refresh_token)
        async with self._session.post('https://discord.com/api/oauth2/token/revoke', data=form) as res:
            return await res.json()

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

    async def _request(self, method: str, url: str, retry=5, **options) -> Optional[dict]:
        cached = self._cache[method, url]
        if cached is not None:
            return cached

        while retry:
            await self._ratelimit.wait()

            async with self._throttle_route((method, url)):

                self.log.debug(f'{method} {url}')
                async with self._session.request(method, url, **options) as res:
                    self.log.debug(f'Received {url}')

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

    async def get(self, endpoint: str) -> Optional[dict]:
        """Make a GET request to a Discord API."""
        return await self._request('GET', api_endpoint(endpoint), headers={'Authorization': f'Bearer {self._access}'})

    async def autorefresh(self, coro_func: Callable[[], Coroutine]):
        """Try to make an API request, and if it fails, try to get a new access token.

        :raises DiscordUnauthorized: (re-raised) if Discord will not grant a new token.
        """
        try:
            return await coro_func()
        except DiscordUnauthorized:
            tokens = await self.refresh_tokens(self._refresh)
            if not tokens:
                raise
            self._access = tokens['access_token']
            self._refresh = tokens['refresh_token']
            return await self.autorefresh(coro_func)

    async def fetch_user_guilds(self) -> list[PartialGuild]:
        """Fetch the currently authenticated user's joined guilds."""
        guilds = await self.autorefresh(lambda: self.get('/users/@me/guilds'))
        if guilds is None:
            return None
        return [PartialGuild.from_dict(g) for g in guilds]

    async def fetch_user(self) -> Optional[PartialUser]:
        """Fetch the currently authenticated user's user profile."""
        data = await self.autorefresh(lambda: self.get('/users/@me'))
        return data and PartialUser.from_dict(data)

    async def close(self):
        """Close the aiohttp session."""
        if self._session:
            await self._session.close()


class DiscordUnauthorized(Exception):
    """Exception indicating an OAuth workflow failed."""

    pass


@dataclass
class PartialUser:
    """Dataclass for a Discord user object."""

    id: int
    name: str
    icon: str

    @classmethod
    def from_dict(cls, data: dict):
        """Create a `PartialUser` from a Discord response."""
        return cls(id=data['id'], name=data['username'], icon=data['avatar'])

    @property
    def icon_url(self) -> str:
        """Create the URL to the user's icon."""
        return f'{CDN_PREFIX}/avatars/{self.id}/{self.icon}.png'

    def __post_init__(self):
        self.id = int(self.id)


@dataclass
class PartialGuild:
    """Dataclass for a Discord guid object."""

    id: int
    name: str
    icon: str
    joined: bool
    perms: Permissions2

    @classmethod
    def from_dict(cls, data: dict):
        """Create a `PartialGuild` from a Discord response."""
        return cls(id=data['id'], name=data['name'], joined=False,
                   icon=data['icon'], perms=data['permissions'])

    @property
    def icon_url(self) -> str:
        """Create the URL to the guild's icon."""
        return f'{CDN_PREFIX}/icons/{self.id}/{self.icon}.png'

    def __post_init__(self):
        self.id = int(self.id)
        self.perms = Permissions2(int(self.perms or 0))
