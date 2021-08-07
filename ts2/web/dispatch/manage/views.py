# manage.py
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

from asgiref.sync import async_to_sync, sync_to_async
from discord import Forbidden, Guild
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import View

from ts2.discord.apps import get_extensions
from ts2.discord.middleware import get_ctx, require_server_access
from ts2.discord.models import Server
from ts2.discord.schema.ext.logging import iter_logging_conf
from ts2.discord.thread import get_thread

from ...models import User, manage_permissions_required


def user_invited_guild(user: User, guild_id: str) -> bool:
    return user.invited_servers.filter(snowflake__exact=guild_id).exists()


@login_required
@require_server_access('read', exists=False)
def index(req: HttpRequest, **kwargs) -> HttpResponse:
    ctx = get_ctx(req)
    if ctx.server or ctx.check_access('execute'):
        return render(req, 'ts2/manage/index.html')
    return redirect('web:index')


@login_required
@require_server_access('read')
def core(req: HttpRequest, **kwargs) -> HttpResponse:
    current_user = req.user
    ctx = get_ctx(req)
    server_invited_by = ctx.server.invited_by
    if (server_invited_by is not None
            and server_invited_by == current_user
            or server_invited_by is None):
        access_control = True
    else:
        access_control = False

    enabled = ctx.server.extensions
    exts = [(app.label, app.icon_and_title, app.label in enabled)
            for app in get_extensions()]

    return render(
        req, 'ts2/manage/core.html',
        context={
            'access_control': access_control,
            'extensions': exts,
        },
    )


@login_required
@require_server_access('read')
def acl_config(req: HttpRequest, **kwargs) -> HttpResponse:
    return render(req, 'ts2/manage/acl.html')


@login_required
@require_server_access('read')
def logging_config(req: HttpRequest, **kwargs) -> HttpResponse:
    logging_conf = sorted((
        (key, conf['name'], conf.get('superuser', False))
        for key, conf in iter_logging_conf(req.user)
    ), key=lambda t: t[2])
    return render(req, 'ts2/manage/logging.html', context={
        'logging_conf': logging_conf,
    })


class DeleteServerProfileView(View):
    @staticmethod
    @login_required
    @manage_permissions_required
    @require_server_access('execute')
    def get(req: HttpRequest, guild_id: str) -> HttpResponse:
        if req.user.is_staff or user_invited_guild(req.user, guild_id):
            return render(req, 'ts2/manage/leave.html')
        raise PermissionDenied()

    @staticmethod
    @login_required
    @manage_permissions_required
    @require_server_access('execute')
    @async_to_sync
    async def post(req: HttpRequest, guild_id: str) -> HttpResponse:
        guild_id = req.POST.get('guild_id')
        if not req.user.is_staff or not await sync_to_async(user_invited_guild)(req.user, guild_id):
            raise PermissionDenied()
        try:
            guild_id = int(guild_id)
        except ValueError:
            guild_id = None
        if not guild_id:
            raise SuspiciousOperation('Invalid parameters.')

        @sync_to_async(thread_sensitive=False)
        def delete_server():
            try:
                server: Server = Server.objects.get(snowflake=guild_id)
            except Server.DoesNotExist:
                return
            server.delete()

        async def leave(bot):
            try:
                guild: Guild = await bot.fetch_guild(guild_id)
            except Forbidden:
                pass
            else:
                await guild.leave()
            await delete_server()

        thread = get_thread()
        thread.run_coroutine(leave(thread.client))

        return redirect(reverse('web:manage.index', kwargs={'guild_id': guild_id}))


class ResetServerDataView(View):
    @staticmethod
    @login_required
    @manage_permissions_required
    @require_server_access('execute')
    def get(req: HttpRequest, guild_id: str) -> HttpResponse:
        return render(req, 'ts2/manage/reset.html')

    @staticmethod
    @login_required
    @manage_permissions_required
    @require_server_access('execute')
    def post(req: HttpRequest, guild_id: str) -> HttpResponse:
        guild_id = req.POST.get('guild_id')
        try:
            guild_id = int(guild_id)
        except ValueError:
            guild_id = None
        if not guild_id:
            raise SuspiciousOperation('Invalid parameters.')

        ctx = req.discord
        ctx.server.delete()

        return redirect(reverse('web:manage.index', kwargs={'guild_id': guild_id}))
