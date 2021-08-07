# server.py
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

import asyncio
from collections import defaultdict
from collections.abc import Generator
from contextlib import suppress
from typing import TypeVar

from asgiref.sync import sync_to_async
from discord import Guild, Object
from discord.abc import ChannelType, GuildChannel
from django.db import IntegrityError, OperationalError, transaction
from django.db.models.query import QuerySet
from more_itertools import always_reversible

from . import models
from .models import Server

DiscordModel = TypeVar('DiscordModel', models.Entity, models.ModelTranslator)

_server_is_fresh: defaultdict[int, asyncio.Event] = defaultdict(asyncio.Event)


def channels_ordered_1d(guild: Guild) -> Generator[GuildChannel]:
    for cat, channels in guild.by_category():
        if cat:
            yield cat
        for c in channels:
            yield c


def text_channels_ordered_1d(guild: Guild) -> Generator[GuildChannel]:
    for c in channels_ordered_1d(guild):
        if c.type in (ChannelType.text, ChannelType.news, ChannelType.category):
            yield c


def _sync_models(model: DiscordModel, designated: list[Object],
                 registered: QuerySet):
    designated = {r.id: r for r in designated}
    registered_ids: set[int] = {d['snowflake'] for d in registered.values('snowflake')}
    to_delete = registered.exclude(snowflake__in=designated.keys())
    to_insert = (model.from_discord(r) for k, r in designated.items()
                 if k not in registered_ids)
    to_update = (model.from_discord(r) for k, r in designated.items()
                 if k in registered_ids)
    to_delete.delete()
    model.objects.bulk_create(to_insert)
    model.objects.bulk_update(to_update, model.updatable_fields())


def _sync_role_layout(server: Server, guild: Guild):
    role_order = {r.id: idx for idx, r in enumerate(always_reversible(guild.roles))}
    server.roles.bulk_update([
        models.Role(snowflake=k, order=v) for k, v in role_order.items()
    ], ['order'])


def _sync_channel_layout(server: Server, guild: Guild):
    channel_order = {c.id: idx for idx, c in enumerate(channels_ordered_1d(guild))}
    server.channels.bulk_update([
        models.Channel(snowflake=k, order=v) for k, v in channel_order.items()
    ], ['order'])


def _sync_server(guild: Guild, *, info=True, roles=True, channels=True, layout=True):
    try:
        server: Server = (
            Server.objects
            .prefetch_related('channels', 'roles')
            .get(pk=guild.id)
        )
    except Server.DoesNotExist:
        return
    with transaction.atomic(), suppress(OperationalError, IntegrityError):
        if info:
            server.name = guild.name
            server.perms = guild.default_role.permissions.value
            server.save()
        if roles:
            _sync_models(models.Role, guild.roles, server.roles)
        if channels:
            _sync_models(models.Channel, [*channels_ordered_1d(guild)], server.channels)
        if layout:
            if roles:
                _sync_role_layout(server, guild)
            if channels:
                _sync_channel_layout(server, guild)


def mark_stale(guild: Guild):
    _server_is_fresh[guild.id].clear()


def mark_fresh(guild: Guild):
    _server_is_fresh[guild.id].set()


def is_up_to_date(guild: Guild):
    return _server_is_fresh[guild.id].is_set()


async def wait_until_synced(guild: Guild):
    return await _server_is_fresh[guild.id].wait()


@sync_to_async(thread_sensitive=False)
def sync_server_unsafe(*args, **kwargs):
    return _sync_server(*args, **kwargs)


@sync_to_async
def sync_server_threadsafe(guild: Guild, **kwargs):
    if is_up_to_date(guild):
        return
    return _sync_server(guild, **kwargs)


async def sync_server(guild: Guild, **kwargs):
    mark_stale(guild)
    await sync_server_threadsafe(guild, **kwargs)
    mark_fresh(guild)
