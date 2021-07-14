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

import asyncio
import logging
from collections.abc import Generator, Iterable
from typing import Optional, Protocol, TypeVar

import aiohttp
from asgiref.sync import sync_to_async
from discord import (AllowedMentions, Client, Guild, Message, MessageReference,
                     Object, Permissions, RawReactionActionEvent)
from discord.abc import ChannelType, GuildChannel
from discord.ext.commands import Bot, Command, has_guild_permissions
from discord.utils import escape_markdown
from django.conf import settings
from django.core.cache import caches
from django.db import IntegrityError
from django.db.models.query import QuerySet
from more_itertools import always_reversible

from ts2.utils.datetime import utcnow, utctimestamp
from ts2.utils.db import async_atomic
from ts2.utils.importutil import objpath

from . import constraint, extension, ipc, models
from .apps import DiscordBotConfig
from .command import Ensemble, Instruction
from .context import Circumstances, CommandContextError
from .ext import autodoc as doc
from .ext.autodoc import (Documentation, Manual, NoSuchCommand,
                          explain_exception)
from .ext.converters.patterns import Choice
from .logging import log_command_errors
from .models import Blacklisted, Server
from .utils import events
from .utils.markdown import code, em, strong

T = TypeVar('T', bound=Client)
U = TypeVar('U', bound=Bot)

AdaptableModel = TypeVar('AdaptableModel', models.Entity, models.ModelTranslator)

HelpFormat = Choice[Documentation.HELP_STYLES.keys(), 'info category']


class DiscordModel(Protocol):
    id: int


class CommandIterator(Protocol):
    commands: Iterable[Command]


class Gatekeeper:
    def __init__(self):
        self.log = logging.getLogger('discord.gatekeeper')
        self._query = Blacklisted.objects.values_list('snowflake', flat=True)

    @sync_to_async
    def add(self, obj: Object):
        try:
            blacklisted = Blacklisted(snowflake=obj.id)
            blacklisted.save()
        except IntegrityError:
            return

    @sync_to_async
    def discard(self, obj: Object):
        try:
            blacklisted = Blacklisted.objects.get(snowflake=obj.id)
            blacklisted.delete()
        except Blacklisted.DoesNotExist:
            return

    async def match(self, *entities: Object) -> bool:
        blacklisted = await self.blacklisted()
        return any(o.id in blacklisted for o in entities)

    @sync_to_async
    def blacklisted(self) -> set[int]:
        return set(self._query.all())

    async def on_message(self, message: Message):
        return not await self.match(message, message.guild, message.channel, message.author)

    async def on_reaction_add(self, reaction, member):
        return not await self.match(member)

    async def on_raw_reaction_add(self, evt: RawReactionActionEvent):
        entities = [Object(id_) for id_ in (evt.guild_id, evt.channel_id,
                                            evt.message_id, evt.user_id)]
        return not await self.match(*entities)

    async def handle(self, event_name: str, *args, **kwargs) -> bool:
        handler = getattr(self, f'on_{event_name}', None)
        if not handler:
            return True
        try:
            return await handler(*args, **kwargs)
        except Exception as e:
            self.log.error('Error while evaluating gatekeeper '
                           f'criteria for {event_name}', exc_info=e)
            return True


class Robot(Bot):
    DEFAULT_PREFIX = 't;'
    DEFAULT_PERMS = Permissions(805825782)

    def __init__(self, *, loop: asyncio.AbstractEventLoop = None, **options):

        options['allowed_mentions'] = AllowedMentions(everyone=False, roles=False, users=True, replied_user=False)
        super().__init__(loop=loop, command_prefix=self.which_prefix,
                         help_command=None, case_insensitive=True, **options)

        self.log = logging.getLogger('discord.bot')
        self.manual: Manual
        self.request: aiohttp.ClientSession

        add_event_listeners(self)
        register_base_commands(self)

        self._init_ipc()
        self._load_extensions()
        self._create_manual()

        self.gatekeeper = Gatekeeper()

    def instruction(self, *args, **kwargs):
        return super().command(*args, cls=Instruction, **kwargs)

    def ensemble(self, *args, invoke_without_command=False, **kwargs):
        return super().group(
            *args, cls=Ensemble,
            invoke_without_command=invoke_without_command,
            **kwargs,
        )

    def _init_ipc(self):
        thread = ipc.CachePollingThread('discord')
        thread.add_event_listener('ts2.discord.bot.refresh', sync_to_async(self._load_extensions))
        thread.start()

    async def _init_client_session(self):
        if hasattr(self, 'request'):
            await self.request.close()
        self.request = aiohttp.ClientSession(
            loop=asyncio.get_running_loop(),
            headers={'User-Agent': settings.USER_AGENT},
        )
        self.log.info('Started an aiohttp.ClientSession')

    def _register_commands(self):
        register_base_commands(self)

    def _load_extensions(self, *args, **kwargs):
        app = DiscordBotConfig.get()
        for label, ext in app.ext_map.items():
            cog_cls = ext.target
            self.log.debug(f'Loaded extension: {label} {objpath(cog_cls)}')
            self.add_cog(cog_cls(label, self))

    def _create_manual(self):
        self.manual = Manual.from_bot(self)
        self.manual.finalize()

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
    def _sync_models(cls, model: AdaptableModel, designated: list[DiscordModel],
                     registered: QuerySet[AdaptableModel]):
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
    def sync_server(cls, guild: Guild, *, roles=True, channels=True, layout=True):
        try:
            server: Server = (
                Server.objects
                .prefetch_related('channels', 'roles')
                .get(pk=guild.id)
            )
        except Server.DoesNotExist:
            server = Server(snowflake=guild.id)
        server.name = guild.name
        server.perms = guild.default_role.permissions.value
        server.save()
        if roles:
            cls._sync_models(models.Role, guild.roles, server.roles)
        if channels:
            cls._sync_models(models.Channel, [*cls.text_channels_ordered_1d(guild)], server.channels)
        if layout:
            cls._sync_layouts(server, guild)

    async def fetch_raw_member(self, guild_id: int, user_id: int) -> dict:
        return await self._get_state().http.get_member(guild_id, user_id)

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
        caches['discord'].set('ts2.discord.bot.refresh', True)

    async def get_context(self, message, *, cls=Circumstances) -> Circumstances:
        ctx: Circumstances = await super().get_context(message, cls=cls)
        if ctx.command and ctx.command.hidden:
            ctx.command = None
            return ctx
        await ctx.init()
        return ctx

    def dispatch(self, event_name, *args, **kwargs):
        task = asyncio.create_task(self.gatekeeper.handle(event_name, *args, **kwargs))

        def callback(task: asyncio.Task):
            try:
                should_dispatch = task.result()
            except Exception:
                pass
            else:
                if not should_dispatch:
                    return
            return super(type(self), self).dispatch(event_name, *args, **kwargs)

        task.add_done_callback(callback)

    async def before_identify_hook(self, shard_id, *, initial=False):
        await self._init_client_session()
        return await super().before_identify_hook(shard_id, initial=initial)

    async def on_ready(self):
        self.log.info('Bot ready')
        self.log.info(f'User {self.user}')

    async def on_message(self, message):
        try:
            return await super().on_message(message)
        except Exception as exc:
            ctx = await self.get_context(message)
            try:
                raise CommandContextError(exc) from exc
            except CommandContextError as exc:
                return await log_command_errors(ctx, exc)

    async def on_command_error(self, ctx: Circumstances, exc: Exception):
        try:
            await explain_exception(ctx, exc)
        except Exception as exc:
            try:
                raise CommandContextError(exc) from exc
            except CommandContextError as exc:
                return await log_command_errors(ctx, exc)
        await log_command_errors(ctx, exc)

    @staticmethod
    @doc.description('Get help about commands.')
    @doc.argument('category', 'What kind of help info to get.')
    @doc.argument('query', 'A command name, such as "echo" or "prefix set".')
    @doc.invocation((), 'See all commands.')
    @doc.invocation(('query',), 'See help for a command.')
    @doc.invocation(('category',), False)
    @doc.invocation(('category', 'query'), 'See specific info about a command, such as argument types.')
    @doc.example('perms', f'Check help doc for {code("perms")}')
    @doc.example('full perms', f'See detailed information about the command {code("perms")}')
    @doc.example('prefix set', f'Check help doc for {code("prefix set")}, where {code("set")} is a subcommand of {code("prefix")}')
    async def send_help(ctx: Circumstances, category: Optional[HelpFormat] = 'normal',
                        *, query: str = ''):
        man = ctx.bot.manual
        query = query.lower()

        if not query:
            return await man.send_toc(ctx)

        if query[:len(ctx.prefix)] == ctx.prefix:
            query = query[len(ctx.prefix):]

        try:
            doc = man.lookup(query)
        except NoSuchCommand as exc:
            return await ctx.send(str(exc), delete_after=60)

        rich_help, text_help = doc.rich_helps[category], doc.text_helps[category]
        if category == 'normal':
            rich_help = rich_help.set_footer(text=f'Use "{ctx.prefix}{ctx.invoked_with} full {query}" for more info')

        return await ctx.reply_with_text_fallback(rich_help, text_help)


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

    @self.listen('on_message')
    async def on_bare_mention(msg: Message):
        if msg.content == f'<@!{self.user.id}>':
            prefixes = await self.which_prefix(self, msg)
            return await msg.reply(f'Prefix is {strong(prefixes[0])}')

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
    @events.event_filter(sync_to_async(events.emote_added))
    @events.event_filter(sync_to_async(events.emote_no_bots))
    @events.event_filter(sync_to_async(events.emote_matches('🗑')))
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

    @self.listen('on_guild_channel_create')
    @self.listen('on_guild_channel_update')
    @self.listen('on_guild_channel_delete')
    async def update_channels(channel, updated=None):
        updated = updated or channel
        self.log.info(f'Updating channels for {updated.guild}')
        await self.sync_server(updated.guild, roles=False)

    @self.listen('on_guild_role_create')
    @self.listen('on_guild_role_update')
    @self.listen('on_guild_role_delete')
    async def update_roles(role, updated=None):
        updated = updated or role
        self.log.info(f'Updating roles for {updated.guild}')
        await self.sync_server(role.guild, channels=False)

    @self.listen('on_guild_update')
    async def update_server(before: Guild, after: Guild):
        self.log.info(f'Updating server info for {after}')
        await self.sync_server(after, roles=False, channels=False, layout=False)

    @self.listen('on_guild_available')
    async def update_server_initial(guild: Guild):
        await self.sync_server(guild)


def register_base_commands(self: Robot):

    self.instruction('help')(self.send_help)

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
    async def ping(ctx: Circumstances):
        await ctx.send(f':PONG {utctimestamp()}')

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
    @doc.restriction(has_guild_permissions, manage_guild=True)
    async def set_prefix(ctx: Circumstances, prefix: str):
        try:
            await ctx.set_prefix(prefix)
            await get_prefix(ctx)
        except ValueError as e:
            await ctx.send(f'{strong("Error:")} {e}')
            raise
