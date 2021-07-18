# middleware.py
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

from dataclasses import dataclass
from typing import Optional

from asgiref.sync import sync_to_async
from discord.errors import HTTPException
from django.apps import apps
from django.contrib import messages
from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from ts2.discord.fetch import (DiscordCache, DiscordFetch, DiscordUnauthorized,
                               PartialGuild, PartialUser)
from ts2.discord.models import Server

from .config import CommandAppConfig, Extensions
from .models import User


def _http_safe_method(req: HttpRequest) -> bool:
    return req.method in ('GET', 'HEAD', 'OPTIONS')


async def fetch_discord_info(req: HttpRequest, view_func):
    user: User = req.user

    @sync_to_async
    def is_authenticated():
        return user.is_authenticated

    if not await is_authenticated():
        return None, None, None

    token = await user.fresh_token()
    if not token:
        raise Logout

    fetch = DiscordFetch(
        user_id=user.snowflake,
        nocache=(
            not getattr(view_func, 'csrf_exempt', False)
            and not _http_safe_method(req)
        ),
    )
    await fetch.init_session(access_token=token, refresh_token=user.refresh_token)

    try:
        guilds = await fetch.fetch_user_guilds()
        profile = await fetch.fetch_user()
    except DiscordUnauthorized:
        raise Logout
    finally:
        await fetch.close()

    if guilds is None:
        raise Logout

    return token, profile, guilds


def invalidate_cache(req: HttpRequest):
    ctx = get_ctx(req)
    user_id = ctx.user_id
    cache = DiscordCache(user_id)
    cache.invalidate()


async def logout_current_user(req: HttpResponse) -> HttpResponse:
    await sync_to_async(logout)(req)
    messages.warning(req, 'Your Discord login credentials have expired. Please log in again.')
    return render(req, 'telescope2/web/index.html')


@sync_to_async
def disable_server(server: Server):
    server.disabled = True
    server.save()


def message_server_disabled(req):
    messages.error(req, ('The bot no longer has access to this server. '
                         'You must manually invite the bot again to continue managing the bot in this server.'))


async def handle_discord_forbidden(req: HttpRequest) -> HttpResponse:
    message_server_disabled(req)
    invalidate_cache(req)
    ctx = get_ctx(req)
    await disable_server(ctx.server)
    return redirect(reverse('web:manage.index', kwargs={'guild_id': ctx.server_id}))


def handle_server_disabled(req: HttpRequest) -> HttpResponse:
    message_server_disabled(req)
    ctx = get_ctx(req)
    redirect_url = reverse('web:manage.index', kwargs={'guild_id': ctx.server_id})
    if redirect_url == req.path:
        return render(req, 'telescope2/web/manage/index.html')
    return redirect(redirect_url)


async def load_servers(req: HttpRequest, guilds: list[PartialGuild]):
    managed_guilds = {g.id: g for g in guilds if g.perms.manage_guild is True}

    @sync_to_async
    def get_servers():
        return [*Server.objects.filter(snowflake__in=managed_guilds)]

    servers: list[Server] = await get_servers()
    server_ids = {s.snowflake for s in servers}

    for v in managed_guilds.values():
        v.joined = v.id in server_ids

    return managed_guilds


@dataclass
class DiscordContext:
    access_token: str

    web_user: User
    user_profile: PartialUser

    servers: dict[int, PartialGuild]
    server_id: Optional[int] = None
    server: Optional[Server] = None

    def __post_init__(self):
        try:
            self.server_id = int(self.server_id)
        except (TypeError, ValueError):
            self.server_id = None

    def accessible(self, server_id: int) -> bool:
        return int(server_id) in self.servers

    @property
    def info(self) -> Optional[PartialGuild]:
        return self.servers.get(self.server_id)

    @property
    def joined(self) -> bool:
        return self.server_id in self.joined_servers

    @property
    def joined_servers(self) -> dict[int, PartialGuild]:
        return {k: v for k, v in self.servers.items() if v.joined}

    @property
    def pending_servers(self) -> dict[int, PartialGuild]:
        return {k: v for k, v in self.servers.items() if not v.joined}

    @property
    def extensions(self) -> dict[str, tuple[bool, CommandAppConfig]]:
        extensions: Extensions = apps.get_app_config('discord').extensions
        if not self.server:
            return {label: (False, conf) for label, conf in extensions.items()}
        enabled = self.server.extensions
        return {label: (label in enabled, conf) for label, conf in extensions.items()}

    @property
    def user_id(self):
        return self.web_user.snowflake

    @property
    def username(self):
        return self.web_user.username

    @property
    def is_staff(self):
        return self.web_user.is_staff

    @property
    def is_superuser(self):
        return self.web_user.is_superuser


class DiscordContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        return self.get_response(request)

    async def process_view(self, request: HttpRequest, view_func,
                           view_args: tuple, view_kwargs: dict):
        try:
            token, profile, guilds = await fetch_discord_info(request, view_func)
        except Logout:
            return await logout_current_user(request)

        if token is None:
            return

        guild_id: str = view_kwargs.get('guild_id')

        servers = await load_servers(request, guilds)

        context = DiscordContext(
            token, request.user,
            profile, servers,
            server_id=guild_id,
        )
        if context.server_id and context.info is None:
            return redirect(reverse('web:index'))

        request.discord = context

        @sync_to_async
        def get_preferences():
            if context.server_id is None:
                return None
            try:
                return Server.objects.get(snowflake=context.server_id)
            except Server.DoesNotExist:
                return None

        context.server = await get_preferences()
        if context.server and context.server.disabled:
            return handle_server_disabled(request)

    async def process_exception(self, request: HttpRequest, exception: Exception):
        if isinstance(exception, Logout):
            return await logout_current_user(request)
        if isinstance(exception, HTTPException):
            return await handle_discord_forbidden(request)
        if isinstance(exception, ServerDisabled):
            return handle_server_disabled(request)


class Logout(Exception):
    pass


class ServerDisabled(Exception):
    pass


def get_ctx(req: HttpRequest, logout: bool = True) -> DiscordContext:
    try:
        return req.discord
    except AttributeError:
        if logout:
            raise PermissionDenied('Bad credentials')
        return None
