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
from contextlib import suppress
from typing import TypeVar

import aiohttp
from asgiref.sync import sync_to_async
from discord import (AllowedMentions, Client, Guild, Intents, Message, Object,
                     Permissions, RawReactionActionEvent)
from discord.ext.commands import (Bot, CommandInvokeError, CommandNotFound,
                                  has_guild_permissions)
from discord.utils import escape_markdown
from django.conf import settings
from django.db import IntegrityError

from ..conf.versions import list_versions
from . import cog
from .apps import get_app, get_constant, server_allowed
from .context import Circumstances
from .ext import autodoc as doc
from .ext import dm
from .ext.acl import acl
from .ext.autodoc import Manual, explain_exception, explains
from .ext.logging import log_command_error, log_exception
from .models import Blacklisted, Server
from .server import sync_server
from .utils.async_ import async_atomic
from .utils.common import Embed2, is_direct_message
from .utils.datetime import utcnow, utctimestamp
from .utils.markdown import code, em, strong

T = TypeVar('T', bound=Client)
U = TypeVar('U', bound=Bot)

log_exception('Disabled module called', level=logging.INFO)(cog.ModuleDisabled)


@explains(CommandNotFound, 'Command not found', 100)
async def on_command_not_found(ctx: Circumstances, exc: CommandNotFound):
    if is_direct_message(ctx):
        return False
    cmd = ctx.searched_path or ctx.full_invoked_with
    try:
        ctx.bot.manual.lookup(cmd)
        return False
    except Exception as e:
        return str(e), 20


@explains(cog.ModuleDisabled, 'Command disabled')
async def on_disabled(ctx, exc: cog.ModuleDisabled):
    return f'This command belongs to the {exc.module} module, which has been disabled.', 20


class RollbackCommand(Exception):
    pass


class Robot(Bot):
    DEFAULT_PREFIX = 't;'
    DEFAULT_PERMS = Permissions(261959446262)

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

    async def get_context(self, message: Message, *args, **kwargs) -> Circumstances:
        ctx: Circumstances = await super().get_context(message, cls=Circumstances)
        try:
            await ctx.init()
        except Server.DoesNotExist:
            if ctx.command:
                await message.send('The bot is misconfigured in this server.')
            ctx.command = None
        if ctx.command and ctx.command.hidden:
            ctx.command = None
        return ctx

    async def invoke(self, ctx: Circumstances):
        with suppress(RollbackCommand):
            async with async_atomic():
                await super().invoke(ctx)
                await self.on_command_returned(ctx)
                if ctx.command_failed:
                    raise RollbackCommand()

    async def on_command_returned(self, ctx: Circumstances):
        if ctx.subcommand_not_completed:
            await ctx.command.dispatch_error(ctx, CommandNotFound())

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
            exc = CommandInvokeError(exc)
            ctx = await self.get_context(message)
            return await self.on_command_error(ctx, exc)

    async def on_command_error(self, ctx: Circumstances, exc: Exception):
        try:
            await explain_exception(ctx, exc)
        except Exception as exc:
            exc = CommandInvokeError(exc)
            return await log_command_error(ctx, ctx.logconfig, exc)
        await log_command_error(ctx, ctx.logconfig, exc)

    @staticmethod
    @dm.accepts_dms
    @doc.description('Get help about commands.')
    @doc.argument('query', 'A command name, such as "echo" or "prefix set".')
    @doc.invocation((), 'See all commands.')
    @doc.invocation(('query',), 'See help for a command.')
    async def send_help(ctx: Circumstances, *, query: str = ''):
        return await ctx.bot.manual.do_help(ctx, query)

    def command_is_hidden(self, cmd):
        return self.manual.commands[cmd.qualified_name].invisible


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
        self.log.debug(f'Updating channels for {updated.guild}; reason: {repr(updated)}')
        await sync_server(updated.guild, info=False, roles=False)

    @self.listen('on_guild_role_create')
    @self.listen('on_guild_role_update')
    @self.listen('on_guild_role_delete')
    async def update_roles(role, updated=None):
        updated = updated or role
        self.log.debug(f'Updating roles for {updated.guild}; reason: {repr(updated)}')
        await sync_server(role.guild, info=False, channels=False)

    @self.listen('on_guild_update')
    async def update_server(before: Guild, after: Guild):
        self.log.debug(f'Updating server info for {after}; reason: {repr(after)}')
        await sync_server(after, roles=False, channels=False, layout=False)

    @self.listen('on_guild_available')
    async def update_server_initial(guild: Guild):
        if not server_allowed(guild.id):
            self.log.warning(f'{guild} is not in the list of allowed guilds!')
            return await guild.leave()
        await sync_server(guild)


def register_base_commands(self: Robot):
    self.command('help')(self.send_help)

    @self.command('about')
    @doc.description('Print info about the bot.')
    async def about(ctx: Circumstances, *, rest: str = None):
        versions = ' '.join([code(f'{pkg}/{v}') for pkg, v
                             in list_versions().items()])
        info = await ctx.bot.application_info()
        embed = (
            Embed2(title=info.name, description=info.description)
            .add_field(name='Owner', value=info.owner.mention)
            .add_field(name='Versions', value=versions, inline=False)
            .set_thumbnail(url=info.icon_url)
            .personalized(ctx.me)
        )
        return await ctx.send(embed=embed)

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
