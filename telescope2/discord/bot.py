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
from typing import (
    Generator, Iterable, List, Optional, Protocol, Set, Tuple, TypeVar,
)

from asgiref.sync import sync_to_async
from discord import (
    AllowedMentions, Client, Guild, Message, MessageReference, Permissions,
    RawReactionActionEvent,
)
from discord.abc import ChannelType, GuildChannel
from discord.ext.commands import Bot, Command, has_guild_permissions
from discord.utils import escape_markdown
from django.core.cache import caches
from django.db import IntegrityError
from django.db.models.query import QuerySet
from more_itertools import always_reversible

from telescope2.utils.datetime import utcnow, utctimestamp
from telescope2.utils.db import async_atomic
from telescope2.utils.functional import finalizer
from telescope2.utils.importutil import objpath

from . import constraint
from . import documentation as doc
from . import extension, ipc, models
from .apps import DiscordBotConfig
from .command import Ensemble, Instruction
from .context import Circumstances
from .documentation import Manual, help_command
from .events import Events
from .logging import log_command_errors
from .models import Server
from .utils.textutil import code, em, strong

T = TypeVar('T', bound=Client)
U = TypeVar('U', bound=Bot)

AdaptableModel = TypeVar('AdaptableModel', models.Entity, models.ModelTranslator)


class DiscordModel(Protocol):
    id: int


class CommandIterator(Protocol):
    commands: Iterable[Command]


class Robot(Bot):
    DEFAULT_PREFIX = 't;'
    DEFAULT_PERMS = Permissions(805825782)

    def __init__(self, *, loop: asyncio.AbstractEventLoop = None, **options):

        options['allowed_mentions'] = AllowedMentions(everyone=False, roles=False, users=True, replied_user=True)
        super().__init__(
            loop=loop, command_prefix=self.which_prefix,
            help_command=None, case_insensitive=True,
            **options,
        )

        self.log = logging.getLogger('discord.bot')
        self.manual: Manual

        add_event_listeners(self)
        register_base_commands(self)

        self._init_ipc()
        self._load_extensions()
        self._create_manual()

    @finalizer(1)
    def instruction(self, *args, **kwargs):
        return super().command(*args, cls=Instruction, **kwargs)

    @finalizer(1)
    def ensemble(self, *args, invoke_without_command=False, **kwargs):
        return super().group(
            *args, cls=Ensemble,
            invoke_without_command=invoke_without_command,
            **kwargs,
        )

    def _init_ipc(self):
        thread = ipc.CachePollingThread('discord')
        thread.add_event_listener('telescope2.discord.bot.refresh', sync_to_async(self._load_extensions))
        thread.start()

    def _register_commands(self):
        register_base_commands(self)

    def _load_extensions(self, *args, **kwargs):
        app = DiscordBotConfig.get()
        for label, ext in app.ext_map.items():
            cog_cls = ext.target
            self.log.info(f'Loaded extension: {label} {objpath(cog_cls)}')
            self.add_cog(cog_cls(label, self))

    def _create_manual(self):
        from .documentation import Manual
        self.manual = Manual.from_bot(self)
        self.manual.finalize()

    async def get_context(self, message, *, cls=Circumstances) -> Circumstances:
        ctx: Circumstances = await super().get_context(message, cls=cls)
        await ctx.init()
        return ctx

    def iter_commands(
        self, root: Optional[CommandIterator] = None, prefix: str = '',
    ) -> Generator[Tuple[str, Command], None, None]:
        for cmd in self.walk_commands():
            yield (cmd.qualified_name, cmd)

    @classmethod
    def channels_ordered_1d(cls, guild: Guild) -> Generator[GuildChannel]:
        for cat, channels in guild.by_category():
            if cat:
                yield cat
            for c in channels:
                yield c

    @classmethod
    def text_channels_ordered_1d(cls, guild: Guild) -> Generator[GuildChannel]:
        for c in cls.channels_ordered_1d(guild):
            if c.type in (ChannelType.text, ChannelType.news, ChannelType.category):
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
        role_order = {r.id: idx for idx, r in enumerate(always_reversible(guild.roles))}
        channel_order = {c.id: idx for idx, c in enumerate(cls.text_channels_ordered_1d(guild))}
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
        cls._sync_models(models.Channel, [*cls.text_channels_ordered_1d(guild)], server.channels)
        cls._sync_layouts(server, guild)

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

    async def on_ready(self):
        self.log.info('Bot ready')
        self.log.info(f'User {self.user}')

    async def on_command_error(self, context, exception):
        return await log_command_errors(context, exception)


def add_event_listeners(self: Robot):

    @self.check_once
    async def command_global_check(ctx: Circumstances) -> bool:
        for check in asyncio.as_completed([
            extension.cog_enabled_check(ctx),
            constraint.command_constraints_check(ctx),
        ]):
            if not await check:
                return False
        return True

    @self.listen('on_guild_join')
    async def on_guild_join(guild: Guild):
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

    @self.listen('on_raw_reaction_add')
    @Events.event_filter(Events.emote_added)
    @Events.event_filter(Events.emote_no_bots)
    @Events.event_filter(Events.emote_matches('🗑'))
    async def handle_reply_delete(evt: RawReactionActionEvent):
        channel: GuildChannel = self.get_channel(evt.channel_id)
        message: Message = await channel.fetch_message(evt.message_id)
        if message.author != self.user:
            return
        reference: MessageReference = message.reference
        if not reference:
            self.log.debug('handle_reply_delete: no reference found')
            return
        reply: Message = await channel.fetch_message(reference.message_id)
        if reply.author.id == evt.user_id:
            await message.delete()


def register_base_commands(self: Robot):
    @self.instruction('echo')
    @doc.description('Send the command arguments back.')
    @doc.argument('text', 'Message to send back.')
    @doc.example('The quick brown fox', em('sends back "The quick brown fox"'))
    async def echo(ctx: Circumstances, *, text: str = None):
        if not text:
            await ctx.send(ctx.message.content)
        else:
            await ctx.send(text)

    @self.instruction('ping')
    @doc.description('Test the network latency between the bot and Discord.')
    async def ping(ctx: Circumstances, *, args: str = None):
        await ctx.send(f':PONG {utctimestamp()}')

    @self.ensemble('prefix', invoke_without_command=True)
    @doc.description('Get the command prefix for the bot in this server.')
    @doc.invocation((), 'Print the prefix.')
    async def get_prefix(ctx: Circumstances):
        prefix = escape_markdown(ctx.server.prefix)
        example = f'Example: {strong(f"{prefix}echo")}'
        await ctx.send(f'Prefix is {strong(prefix)}\n{example}')

    @get_prefix.instruction('set')
    @doc.description('Set a new prefix for this server.')
    @doc.argument('prefix', 'The new prefix to use. Spaces will be trimmed.')
    @doc.example('?', f'Set the command prefix to {code("?")}')
    @has_guild_permissions(manage_guild=True)
    async def set_prefix(ctx: Circumstances, prefix: str):
        try:
            await ctx.set_prefix(prefix)
            await get_prefix(ctx)
        except ValueError as e:
            await ctx.send(f'{strong("Error:")} {e}')
            raise

    @self.listen('on_message')
    async def on_ping(msg: Message):
        gateway_dst = utctimestamp()

        if not self.user:
            return
        if self.user.id != msg.author.id:
            return
        if msg.content[:6] != ':PONG ':
            return

        try:
            msg_created = float(msg.content[6:])
        except ValueError:
            return

        gateway_latency = 1000 * (gateway_dst - msg_created)
        edit_start = utcnow()
        await msg.edit(content=f'Gateway (http send -> gateway receive time): {gateway_latency:.3f}ms')
        edit_latency = (utcnow() - edit_start).total_seconds() * 1000

        await msg.edit(content=f'Gateway: {code(f"{gateway_latency:.3f}ms")}\nHTTP API (Edit): {code(f"{edit_latency:.3f}ms")}')

    self.add_command(help_command)
