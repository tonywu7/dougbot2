# bot.py
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
from importlib import import_module
from pathlib import Path
from typing import (Generator, Iterable, List, Optional, Protocol, Set, Tuple,
                    TypeVar)

from asgiref.sync import sync_to_async
from discord import AllowedMentions, Client, Guild, Message, Permissions
from discord.abc import GuildChannel
from discord.ext.commands import Bot, Command, Group
from django.core.cache import caches
from django.db import IntegrityError
from django.db.models.query import QuerySet

from telescope2.utils.db import async_atomic
from telescope2.utils.importutil import iter_module_tree, objpath

from . import ipc, models
from .apps import DiscordBotConfig
from .context import Circumstances
from .models import Server

T = TypeVar('T', bound=Client)
U = TypeVar('U', bound=Bot)

AdaptableModel = TypeVar('AdaptableModel', models.Entity, models.ModelTranslator)


class DiscordModel(Protocol):
    id: int


class CommandIterator(Protocol):
    commands: Iterable[Command]


class Robot(Bot):
    async def on_ready(self):
        self.log.info('Bot ready')
        self.log.info(f'User {self.user}')

    async def on_guild_join(self, guild: Guild):
        self.log.info(f'Joined {guild}')
        try:
            async with async_atomic():
                await self.create_server(guild)
        except IntegrityError:
            pass
        try:
            async with async_atomic():
                await self.sync_server(guild)
        except IntegrityError:
            pass

    def iter_commands(
        self, root: Optional[CommandIterator] = None, prefix: str = '',
    ) -> Generator[Tuple[str, Command], None, None]:

        root = root or self
        for cmd in root.commands:
            identifier = f'{prefix} {cmd.name}'.strip()
            yield (identifier, cmd)
            if isinstance(cmd, Group):
                yield from self.iter_commands(cmd, identifier)

    @classmethod
    def channels_ordered_1d(cls, guild: Guild) -> Generator[GuildChannel]:
        for cat, channels in guild.by_category():
            yield cat
            for c in channels:
                yield c

    @classmethod
    def _sync_models(cls, model: AdaptableModel, designated: List[DiscordModel],
                     registered: QuerySet[AdaptableModel]):
        designated = {r.id: r for r in designated}
        registered_ids: Set[int] = {d['snowflake'] for d in registered.values('snowflake')}
        to_delete = registered.exclude(snowflake__in=designated.keys())
        to_insert = (model.from_discord(r) for k, r in designated.items()
                     if k not in registered_ids)
        to_update = (model.from_discord(r) for k, r in designated.items()
                     if k in registered_ids)
        to_delete.delete()
        model.objects.bulk_create(to_insert)
        model.objects.bulk_update(to_update, model.updatable_fields())

    @classmethod
    def _sync_layouts(cls, server: Server, guild: Guild):
        role_order = {r.id: idx for idx, r in enumerate(guild.roles)}
        channel_order = {c.id: idx for idx, c in enumerate(cls.channels_ordered_1d(guild)) if c is not None}
        server.roles.bulk_update([
            models.Role(snowflake=k, order=v) for k, v in role_order.items()
        ], ['order'])
        server.channels.bulk_update([
            models.Channel(snowflake=k, order=v) for k, v in channel_order.items()
        ], ['order'])

    @classmethod
    @sync_to_async(thread_sensitive=False)
    def create_server(cls, guild: Guild):
        Server(snowflake=guild.id).save()

    @classmethod
    @sync_to_async(thread_sensitive=False)
    def sync_server(cls, guild: Guild):
        server: Server = (
            Server.objects
            .prefetch_related('channels', 'roles')
            .get(pk=guild.id)
        )
        server.name = guild.name
        server.save()
        cls._sync_models(models.Role, guild.roles, server.roles)
        cls._sync_models(models.Channel, guild.channels, server.channels)
        cls._sync_layouts(server, guild)


class Telescope(Robot):

    DEFAULT_PREFIX = 't;'
    DEFAULT_PERMS = Permissions(805825782)

    def __init__(self, *, loop: asyncio.AbstractEventLoop = None, **options):
        options['allowed_mentions'] = AllowedMentions(everyone=False, roles=False, users=True, replied_user=True)
        super().__init__(loop=loop, command_prefix=self.which_prefix, **options)

        self.log = logging.getLogger('telescope')
        self._register_events()
        self._register_commands()
        self._init_ipc()
        self._load_extensions()

    def _init_ipc(self):
        thread = ipc.CachePollingThread('discord')
        thread.add_event_listener('telescope2.discord.bot.refresh', sync_to_async(self._load_extensions))
        thread.start()

    def _register_events(self):
        self.listen('on_guild_join')(self.on_guild_join)

    def _register_commands(self):
        for parts in iter_module_tree(str(Path(__file__).with_name('commands')), 1):
            module_path = f'.commands.{".".join(parts)}'
            command_module = import_module(module_path, __package__)
            try:
                command_module.register_all(self)
            except AttributeError:
                pass
            else:
                self.log.info(f'Loaded commands from {module_path}')

    @classmethod
    async def _get_prefix(cls, *, bot_id: int, guild_id: int):
        @sync_to_async
        def get():
            return Server.objects.get(pk=guild_id).prefix
        try:
            return [await get(), f'<@!{bot_id}> ']
        except Server.DoesNotExist:
            return [cls.DEFAULT_PREFIX, f'<@!{bot_id}> ']

    @classmethod
    async def which_prefix(cls, bot: Bot, msg: Message):
        bot_id = bot.user.id
        if msg.guild is None:
            return [cls.DEFAULT_PREFIX, f'<@!{bot_id}> ']
        return await cls._get_prefix(bot_id=bot_id, guild_id=msg.guild.id)

    @classmethod
    def schedule_refresh(cls):
        caches['discord'].set('telescope2.discord.bot.refresh', True)

    def _load_extensions(self, *args, **kwargs):
        app = DiscordBotConfig.get()
        for label, ext in app.ext_map.items():
            cog_cls = ext.target
            self.log.info(f'Loaded extension: {label} {objpath(cog_cls)}')
            self.add_cog(cog_cls(self))

    async def get_context(self, message, *, cls=Circumstances) -> Circumstances:
        ctx: Circumstances = await super().get_context(message, cls=cls)
        await ctx.init()
        return ctx
