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

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from functools import wraps
from typing import Literal, Optional, Union
from urllib.parse import urlencode

from asgiref.sync import sync_to_async
from discord.errors import HTTPException
from django.apps import apps
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .apps import server_allowed
from .config import CommandAppConfig, Extensions
from .fetch import (DiscordCache, DiscordFetch, DiscordUnauthorized,
                    PartialGuild, PartialUser)
from .models import Server


def _http_safe_method(req: HttpRequest) -> bool:
    return req.method in ('GET', 'HEAD', 'OPTIONS')


def unsafe(req, view_func):
    return (
        not getattr(view_func, 'csrf_exempt', False)
        and not _http_safe_method(req)
    )


async def fetch_discord_info(req: HttpRequest):
    user: User = req.user

    @sync_to_async
    def is_authenticated():
        return user.is_authenticated

    if not await is_authenticated():
        return None, None, []

    token = await user.fresh_token()
    if not token:
        raise Logout

    fetch = DiscordFetch(user_id=user.pk)
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


@sync_to_async
def invalidate_cache(req: HttpRequest):
    user_id = req.user.pk
    cache = DiscordCache(user_id)
    cache.invalidate()


async def logout_current_user(req: HttpResponse) -> HttpResponse:
    await sync_to_async(logout)(req)
    message = 'Your Discord login credentials have expired. Please log in again.'
    accept = req.headers.get('Accept', '').lower()
    content_type = req.headers.get('Content-Type', '').lower()
    if 'application/json' in accept or 'application/json' in content_type:
        return JsonResponse({'errors': [{'message': message}]})
    messages.warning(req, message)
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
    await invalidate_cache(req)
    ctx = get_ctx(req, logout=False)
    if ctx:
        await disable_server(ctx.server)
    return redirect(reverse('web:manage.index', kwargs={'guild_id': ctx.server_id}))


def handle_server_disabled(req: HttpRequest) -> HttpResponse:
    message_server_disabled(req)
    ctx = get_ctx(req)
    redirect_url = reverse('web:manage.index', kwargs={'guild_id': ctx.server_id})
    if redirect_url == req.path:
        return render(req, 'ts2/manage/index.html')
    return redirect(redirect_url)


AccessLevel = Literal['read', 'write', 'execute']


@dataclass
class DiscordContext:
    access_token: str

    web_user: User
    user_profile: PartialUser

    # All servers the user is in
    servers: dict[int, PartialGuild]

    permissions: defaultdict[int, frozenset[AccessLevel]]

    # Requested server ID
    server_id: Optional[int] = None
    # Current server model, if it exists in the database and is requested
    server: Optional[Server] = None

    @classmethod
    async def create(cls, guilds: Iterable[PartialGuild], guild_id: Optional[str | int],
                     token: str, user: User, profile: PartialUser) -> DiscordContext:
        if guild_id:
            guild_id = int(guild_id)
        user_guilds = {g.id: g for g in guilds}

        @sync_to_async
        def get_servers():
            return {s.snowflake: s for s in Server.objects.filter(snowflake__in=user_guilds)}

        servers: dict[int, Server] = await get_servers()

        for v in user_guilds.values():
            v.joined = v.id in servers

        permissions = defaultdict(set)
        for k, v in user_guilds.items():
            perms = v.perms
            if perms.manage_guild:
                permissions[k] |= {'read', 'write', 'execute'}
                continue
            server = servers.get(k)
            if not server:
                continue
            elif int(server.writable) and perms >= server.writable:
                permissions[k] |= {'read', 'write'}
            elif int(server.readable) and perms >= server.readable:
                permissions[k].add('read')

        permissions = defaultdict(set, {
            k: frozenset(v) for k, v
            in permissions.items()
            if server_allowed(k)
        })

        if 'read' in permissions[guild_id]:
            current = servers.get(guild_id)
        else:
            current = None

        return cls(access_token=token, web_user=user, user_profile=profile,
                   servers=user_guilds, server_id=guild_id, server=current,
                   permissions=permissions)

    def check_access(self, access: AccessLevel, server_id: Optional[Union[str, int]] = None) -> bool:
        server_id = server_id or self.server_id
        try:
            return access in self.permissions[int(server_id)]
        except ValueError:
            return False

    def assert_access(self, access: AccessLevel, server_id: Optional[Union[str, int]] = None) -> None:
        if not self.check_access(access, server_id):
            if self.check_access('read', server_id):
                raise PermissionDenied('You are in read-only mode.')
            raise PermissionDenied('Insufficient permissions.')

    @property
    def readonly(self) -> bool:
        return self.permissions[self.server_id] == frozenset({'read'})

    @property
    def info(self) -> Optional[PartialGuild]:
        return self.servers.get(self.server_id)

    @property
    def joined(self) -> bool:
        return self.server_id in self.joined_servers

    @property
    def joined_servers(self) -> dict[int, PartialGuild]:
        return {k: v for k, v in self.servers.items()
                if v.joined and self.check_access('read', k)}

    @property
    def pending_servers(self) -> dict[int, PartialGuild]:
        return {k: v for k, v in self.servers.items()
                if not v.joined and self.check_access('execute', k)}

    @property
    def extensions(self) -> dict[str, tuple[bool, CommandAppConfig]]:
        extensions: Extensions = apps.get_app_config('discord').extensions
        if not self.server:
            return {label: (False, conf) for label, conf in extensions.items()}
        enabled = self.server.extensions
        return {label: (label in enabled, conf) for label, conf in extensions.items()}

    @property
    def user_id(self):
        return self.web_user.pk

    @property
    def username(self):
        return self.web_user.username

    @property
    def is_staff(self):
        return self.web_user.is_staff

    @property
    def is_superuser(self):
        return self.web_user.is_superuser

    def fetch_server(self, server_id: Union[str, int], access: Literal['read', 'write'],
                     deny=True, queryset=Server.objects) -> Optional[Server]:
        if deny:
            self.assert_access(access, server_id)
            return queryset.get(snowflake=server_id)
        if not self.check_access(access, server_id):
            return None
        return queryset.get(snowflake=server_id)


class DiscordContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        return self.get_response(request)

    async def process_view(self, request: HttpRequest, view_func,
                           view_args: tuple, view_kwargs: dict):

        # Make sure we have the latest auth info from Discord.
        if unsafe(request, view_func):
            await invalidate_cache(request)

        try:
            token, profile, guilds = await fetch_discord_info(request)
        except Logout:
            return await logout_current_user(request)

        guild_id: str = view_kwargs.get('guild_id')
        context = await DiscordContext.create(guilds, guild_id, token, request.user, profile)

        if context.server_id and context.info is None:
            if request.user.is_authenticated:
                return redirect(reverse('web:index'))
            handoff = {'continue': request.get_full_path()}
            return redirect(f'{reverse("web:login")}?{urlencode(handoff)}')
        if context.server and context.server.disabled:
            return handle_server_disabled(request)

        request.discord = context

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


def get_ctx(req: HttpRequest, logout: bool = True) -> Optional[DiscordContext]:
    try:
        return req.discord
    except AttributeError:
        if logout:
            raise PermissionDenied('Bad credentials')
        return None


def require_server_presence(f):
    @wraps(f)
    def check_server(request: HttpRequest, *args, **kwargs):
        ctx = get_ctx(request)
        if not ctx.server:
            return redirect('web:manage.index', kwargs={'guild_id': ctx.server_id})
        return f(request, *args, **kwargs)
    return check_server


def require_server_access(permission: AccessLevel, exists: bool = True):
    def wrapper(view_func):
        @wraps(view_func)
        def check_perm(request: HttpRequest, *args, **kwargs):
            ctx = get_ctx(request, logout=False)
            if not ctx or not ctx.check_access(permission):
                return redirect(reverse('web:index'))
            if exists and not ctx.server:
                return redirect(reverse(
                    'web:manage.index',
                    kwargs={'guild_id': ctx.server_id},
                ))
            return view_func(request, *args, **kwargs)
        return check_perm
    return wrapper
