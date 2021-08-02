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
from collections.abc import Generator
from typing import Optional, TypeVar

import aiohttp
from asgiref.sync import sync_to_async
from discord import (AllowedMentions, Client, Guild, Intents, Message, Object,
                     Permissions, RawReactionActionEvent)
from discord.abc import ChannelType, GuildChannel
from discord.ext.commands import Bot, has_guild_permissions
from discord.utils import escape_markdown
from django.conf import settings
from django.db import IntegrityError
from django.db.models.query import QuerySet
from more_itertools import always_reversible

from ts2.utils.datetime import utcnow, utctimestamp

from . import cog, models
from .apps import get_app, get_constant, server_allowed
from .context import Circumstances, CommandContextError
from .ext import autodoc as doc
from .ext import dm
from .ext.acl import acl
from .ext.autodoc import Documentation, Manual, explain_exception, explains
from .ext.logging import log_command_errors, log_exception
from .ext.types.patterns import Choice
from .models import Blacklisted, Server
from .utils.common import is_direct_message
from .utils.markdown import code, em, strong

T = TypeVar('T', bound=Client)
U = TypeVar('U', bound=Bot)

AdaptableModel = TypeVar('AdaptableModel', models.Entity, models.ModelTranslator)
log_exception('Disabled module called', level=logging.INFO)(cog.ModuleDisabled)

HelpFormat = Choice[[f'-{k}' for k in Documentation.HELP_STYLES], 'info category']


@explains(cog.ModuleDisabled, 'Command disabled')
async def on_disabled(ctx, exc: cog.ModuleDisabled):
    return f'This command belongs to the {exc.module} module, which has been disabled.', 20


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


def _sync_models(model: AdaptableModel, designated: list[Object],
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


def _sync_layouts(server: Server, guild: Guild):
    role_order = {r.id: idx for idx, r in enumerate(always_reversible(guild.roles))}
    channel_order = {c.id: idx for idx, c in enumerate(text_channels_ordered_1d(guild))}
    server.roles.bulk_update([
        models.Role(snowflake=k, order=v) for k, v in role_order.items()
    ], ['order'])
    server.channels.bulk_update([
        models.Channel(snowflake=k, order=v) for k, v in channel_order.items()
    ], ['order'])


@sync_to_async(thread_sensitive=False)
def sync_server(guild: Guild, *, roles=True, channels=True, layout=True):
    try:
        server: Server = (
            Server.objects
            .prefetch_related('channels', 'roles')
            .get(pk=guild.id)
        )
    except Server.DoesNotExist:
        return
    server.name = guild.name
    server.perms = guild.default_role.permissions.value
    server.save()
    if roles:
        _sync_models(models.Role, guild.roles, server.roles)
    if channels:
        _sync_models(models.Channel, [*text_channels_ordered_1d(guild)], server.channels)
    if layout:
        _sync_layouts(server, guild)


class Robot(Bot):
    DEFAULT_PREFIX = 't;'
    DEFAULT_PERMS = Permissions(805825782)

    def __init__(self, *, loop: asyncio.AbstractEventLoop = None, **options):
        options['allowed_mentions'] = AllowedMentions(everyone=False, roles=False, users=True, replied_user=False)
        options['command_prefix'] = self.which_prefix
        options['help_command'] = None
        options.setdefault('intents', Intents.all())
        options.setdefault('case_insensitive', True)
        options.setdefault('strip_after_prefix', True)
        super().__init__(loop=loop, **options)

        self.log = logging.getLogger('discord.bot')
        self.manual: Manual
        self.request: aiohttp.ClientSession

        add_event_listeners(self)
        register_base_commands(self)
        load_extensions(self)
        create_manual(self)
        self.gatekeeper = Gatekeeper()

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

    @classmethod
    async def _get_prefix(cls, *, bot_id: int, guild_id: int):
        @sync_to_async
        def get():
            return Server.objects.get(pk=guild_id).prefix
        return [await get(), f'<@!{bot_id}> ']

    @classmethod
    async def which_prefix(cls, bot: Bot, msg: Message):
        bot_id = bot.user.id
        if msg.guild is None:
            return ['']
        try:
            return await cls._get_prefix(bot_id=bot_id, guild_id=msg.guild.id)
        except Server.DoesNotExist:
            return ['\x00']

    async def get_context(self, message, *, cls=Circumstances) -> Circumstances:
        ctx: Circumstances = await super().get_context(message, cls=cls)
        if ctx.command and ctx.command.hidden:
            ctx.command = None
        if ctx.command:
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

    async def on_message(self, message: Message):
        try:
            return await super().on_message(message)
        except Exception as exc:
            if message.author.bot:
                raise
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
    @dm.accepts_dms
    @doc.description('Get help about commands.')
    @doc.argument('category', 'What kind of help info to get.')
    @doc.argument('query', 'A command name, such as "echo" or "prefix set".')
    @doc.invocation((), 'See all commands.')
    @doc.invocation(('query',), 'See help for a command.')
    @doc.invocation(('category',), False)
    @doc.invocation(('category', 'query'), 'See specific info about a command, such as argument types.')
    @doc.example('perms', f'Check help doc for {code("perms")}')
    @doc.example('-full perms', f'See detailed information about the command {code("perms")}')
    @doc.example('prefix set', f'Check help doc for {code("prefix set")}, where {code("set")} is a subcommand of {code("prefix")}')
    async def send_help(ctx: Circumstances, category: Optional[HelpFormat] = '-normal',
                        *, query: str = ''):
        return await ctx.bot.manual.do_help(ctx, category[1:], query)

    def is_hidden(self, cmd):
        return self.manual.commands[cmd.qualified_name].hidden


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
        return any(o.id in blacklisted for o in entities if o)

    @sync_to_async
    def blacklisted(self) -> set[int]:
        return set(self._query.all())

    async def on_message(self, message: Message):
        return not await self.match(message, message.guild, message.channel, message.author)

    async def on_reaction_add(self, reaction, member):
        return not await self.match(member)

    async def on_raw_reaction_add(self, evt: RawReactionActionEvent):
        entities = [Object(id_) for id_ in (evt.guild_id or 0, evt.channel_id or 0,
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


def add_event_listeners(self: Robot):
    @self.check_once
    async def command_global_check(ctx: Circumstances) -> bool:
        for check in asyncio.as_completed([
            cog.cog_enabled_check(ctx),
            dm.dm_allowed_check(ctx),
        ]):
            if not await check:
                return False
        return True

    @self.check
    async def command_check(ctx: Circumstances) -> bool:
        for check in asyncio.as_completed([
            acl.acl_check(ctx),
        ]):
            if not await check:
                return False
        return True

    @self.listen('on_message')
    async def on_bare_mention(msg: Message):
        if is_direct_message(msg):
            return
        if msg.content == f'<@!{self.user.id}>':
            prefixes = await self.which_prefix(self, msg)
            return await msg.reply(f'Prefix is {strong(prefixes[0])}')

    @self.listen('on_guild_join')
    async def on_guild_join(guild: Guild):
        self.log.info(f'Joined {guild}')
        if not server_allowed(guild.id):
            self.log.warning(f'{guild} is not in the list of allowed guilds!')
            return await guild.leave()

    @self.listen('on_guild_channel_create')
    @self.listen('on_guild_channel_update')
    @self.listen('on_guild_channel_delete')
    async def update_channels(channel, updated=None):
        updated = updated or channel
        self.log.info(f'Updating channels for {updated.guild}')
        await sync_server(updated.guild, roles=False)

    @self.listen('on_guild_role_create')
    @self.listen('on_guild_role_update')
    @self.listen('on_guild_role_delete')
    async def update_roles(role, updated=None):
        updated = updated or role
        self.log.info(f'Updating roles for {updated.guild}')
        await sync_server(role.guild, channels=False)

    @self.listen('on_guild_update')
    async def update_server(before: Guild, after: Guild):
        self.log.info(f'Updating server info for {after}')
        await sync_server(after, roles=False, channels=False, layout=False)

    @self.listen('on_guild_available')
    async def update_server_initial(guild: Guild):
        if not server_allowed(guild.id):
            self.log.warning(f'{guild} is not in the list of allowed guilds!')
            return await guild.leave()
        await sync_server(guild)


def register_base_commands(self: Robot):
    self.command('help')(self.send_help)

    @self.command('echo')
    @dm.accepts_dms
    @doc.description('Send the command arguments back.')
    @doc.argument('text', 'Message to send back.')
    @doc.example('The quick brown fox', em('sends back "The quick brown fox"'))
    async def echo(ctx: Circumstances, *, text: str = None):
        if not text:
            await ctx.send(ctx.message.content)
        else:
            await ctx.send(text)

    @self.command('ping')
    @doc.description('Test the network latency between the bot and Discord.')
    async def ping(ctx: Circumstances):
        await ctx.send(f':PONG {utctimestamp()}')

    @self.group('prefix', invoke_without_command=True)
    @doc.description('Get the command prefix for the bot in this server.')
    @doc.invocation((), 'Print the prefix.')
    async def get_prefix(ctx: Circumstances):
        prefix = escape_markdown(ctx.server.prefix)
        example = f'Example: {strong(f"{prefix}echo")}'
        await ctx.send(f'Prefix is {strong(prefix)}\n{example}')

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

    @get_prefix.command('set')
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


def load_extensions(self: Robot, *args, **kwargs):
    app = get_app()
    for label, ext in app.ext_map.items():
        cog_cls = ext.target
        self.add_cog(cog_cls(label, self))


def create_manual(self: Robot):
    title = f'{get_constant("branding_full")}: Command list'
    color = get_constant('site_color')
    if color:
        color = int(color, 16)
    doc.init_bot(self, title, color)
