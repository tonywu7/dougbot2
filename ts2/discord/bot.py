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
from typing import Literal, Optional

import aiohttp
from asgiref.sync import sync_to_async
from discord import (Activity, ActivityType, AllowedMentions, Forbidden, Game,
                     Guild, Intents, Message, MessageReference, NotFound,
                     Permissions, RawMessageDeleteEvent)
from discord.ext.commands import (Bot, CommandInvokeError, CommandNotFound,
                                  errors, has_guild_permissions, is_owner)
from discord.utils import escape_markdown
from django.conf import settings
from django.core.cache import caches

from ..conf.versions import list_versions
from . import cog, gatekeeper
from .apps import get_app, get_constant, server_allowed
from .context import Circumstances
from .ext import autodoc as doc
from .ext import dm
from .ext.acl import acl
from .ext.autodoc import Manual, add_error_names, explain_exception, explains
from .ext.logging import log_command_error, log_exception
from .ext.types.patterns import Choice
from .models import Server
from .server import sync_server
from .utils.async_ import async_atomic
from .utils.common import Embed2, is_direct_message
from .utils.datetime import utcnow, utctimestamp
from .utils.markdown import code, em, strong

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
    DEFAULT_MENTIONS = AllowedMentions(everyone=False, roles=False,
                                       users=True, replied_user=False)

    _CACHE_VERSION = 1

    def __init__(self, *, loop: asyncio.AbstractEventLoop = None, **options):
        options['allowed_mentions'] = self.DEFAULT_MENTIONS
        options['command_prefix'] = self.which_prefix
        options['help_command'] = None
        options.setdefault('intents', Intents.all())
        options.setdefault('case_insensitive', True)
        options.setdefault('strip_after_prefix', True)
        super().__init__(loop=loop, **options)

        self.log = logging.getLogger('discord.bot')
        self.manual: Manual
        self.request: aiohttp.ClientSession
        self._cache = caches['discord']

        add_base_listeners(self)
        add_reply_listener(self)

        add_base_commands(self)
        add_ping_command(self)
        add_status_command(self)

        self.load_extensions()
        self.create_manual()
        define_errors()

        self.gatekeeper = gatekeeper.Gatekeeper()

    async def _init_client_session(self):
        if hasattr(self, 'request'):
            await self.request.close()
        self.request = aiohttp.ClientSession(
            loop=asyncio.get_running_loop(),
            headers={'User-Agent': settings.USER_AGENT},
        )
        self.log.info('Started an aiohttp.ClientSession')

    @classmethod
    async def get_server_prefix(cls, guild_id: int) -> str:
        @sync_to_async
        def get():
            return Server.objects.get(pk=guild_id).prefix
        return await get()

    @classmethod
    async def which_prefix(cls, bot: Bot, msg: Message):
        if msg.guild is None:
            return ''
        try:
            prefix = await cls.get_server_prefix(msg.guild.id)
            content: str = msg.content
            if content.lower().startswith(prefix.lower()):
                return content[:len(prefix)]
            return '\x00'
        except Server.DoesNotExist:
            return '\x00'

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

    def get_cache_key(self, **keys):
        args = [f'{k}={v}' for k, v in keys.items()]
        return ':'.join([__name__, 'cache', *args])

    def get_cache(self, default=None, /, **keys):
        return self._cache.get(self.get_cache_key(**keys), default, self._CACHE_VERSION)

    def set_cache(self, value, ttl: Optional[float], /, **keys):
        key = self.get_cache_key(**keys)
        self._cache.set(key, value, timeout=ttl, version=self._CACHE_VERSION)

    def del_cache(self, **keys):
        key = self.get_cache_key(**keys)
        self._cache.delete(key, version=self._CACHE_VERSION)

    async def set_exit_status(self):
        await self.change_presence(activity=Game('System Restart. Please hold.'))
        self.log.info('Exit indicator is set!')

    def load_extensions(self):
        app = get_app()
        for label, ext in app.ext_map.items():
            cog_cls = ext.target
            self.add_cog(cog_cls(label, self))

    def create_manual(self):
        title = f'{get_constant("branding_full")}: Command list'
        color = get_constant('site_color')
        if color:
            color = int(color, 16)
        doc.init_bot(self, title, color)


def add_base_listeners(self: Robot):
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
            prefix = await self.get_server_prefix(msg.guild.id)
            example = f'{prefix}echo'
            return await msg.reply(f'Prefix is {strong(prefix)}\nExample command: {strong(example)}')

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
        await sync_server(updated.guild, info=False, roles=False)
        self.log.debug(f'Updated channels for {updated.guild}; reason: {repr(updated)}')

    @self.listen('on_guild_role_create')
    @self.listen('on_guild_role_update')
    @self.listen('on_guild_role_delete')
    async def update_roles(role, updated=None):
        updated = updated or role
        await sync_server(role.guild, info=False, channels=False)
        self.log.debug(f'Updated roles for {updated.guild}; reason: {repr(updated)}')

    @self.listen('on_guild_update')
    async def update_server(before: Guild, after: Guild):
        await sync_server(after, roles=False, channels=False, layout=False)
        self.log.debug(f'Updated server info for {after}; reason: {repr(after)}')

    @self.listen('on_guild_available')
    async def update_server_initial(guild: Guild):
        if not server_allowed(guild.id):
            self.log.warning(f'{guild} is not in the list of allowed guilds!')
            return await guild.leave()
        await sync_server(guild)


def add_reply_listener(self: Robot):
    @self.listen('on_message')
    async def on_bot_reply(msg: Message):
        if msg.author != self.user:
            return
        ref: MessageReference = msg.reference
        if not ref or not ref.cached_message:
            return
        referrer: Message = ref.cached_message
        self.set_cache(msg.id, 31536000, referrer=referrer.id)

    @self.listen('on_raw_message_delete')
    async def on_command_call_delete(ev: RawMessageDeleteEvent):
        channel = self.get_channel(ev.channel_id)
        if not channel:
            return
        referred = self.get_cache(None, referrer=ev.message_id)
        if referred is None:
            return
        self.del_cache(referrer=ev.message_id)
        msg = channel.get_partial_message(referred)
        await msg.delete(delay=0)


def add_base_commands(self: Robot):
    @self.command('help')
    @dm.accepts_dms
    @doc.description('Get help about commands.')
    @doc.argument('query', 'A command name, such as "echo" or "prefix set".')
    @doc.invocation((), 'See all commands.')
    @doc.invocation(('query',), 'See help for a command.')
    async def send_help(ctx: Circumstances, *, query: str = ''):
        return await ctx.bot.manual.do_help(ctx, query)

    @self.command('about')
    @doc.description('Print info about the bot.')
    async def about(ctx: Circumstances, *, rest: str = None):
        versions = ' '.join([code(f'{pkg}/{v}') for pkg, v
                             in list_versions().items()])
        info = await ctx.bot.application_info()
        embed = (
            Embed2(title=info.name, description=info.description)
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
            await ctx.reply(ctx.message.content)
        else:
            await ctx.reply(text)

    @self.group('prefix', invoke_without_command=True)
    @doc.description('Get the command prefix for the bot in this server.')
    @doc.invocation((), 'Print the prefix.')
    async def get_prefix(ctx: Circumstances):
        prefix = escape_markdown(ctx.server.prefix)
        example = f'Example: {strong(f"{prefix}help")}'
        await ctx.send(f'Prefix is {strong(prefix)}\n{example}')

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


def add_ping_command(self: Robot):
    @self.command('ping')
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

        await msg.edit(content=(f'Gateway: {code(f"{gateway_latency:.3f}ms")}'
                                f'\nHTTP API (Edit): {code(f"{edit_latency:.3f}ms")}'))


def add_status_command(self: Robot):
    async def set_presence(kind: str, **kwargs):
        if kind == 'reset':
            await self.change_presence(activity=None)
            self.del_cache(type=f'{__name__}.activity')
            return
        try:
            presence_t = getattr(ActivityType, kind)
        except AttributeError:
            return
        activity = Activity(type=presence_t, **kwargs)
        self.set_cache((kind, kwargs), None, type=f'{__name__}.activity')
        await self.change_presence(activity=activity)

    @self.listen('on_ready')
    async def resume_presence():
        await asyncio.sleep(10)
        kind, kwargs = self.get_cache((None, None), type=f'{__name__}.activity')
        if kind is None:
            return await set_presence('reset')
        await set_presence(kind, **kwargs)

    @self.command('status')
    @doc.description("Change the bot's status.")
    @doc.argument('activity', 'The type of activity.')
    @doc.argument('name', 'The description of the status.')
    @doc.restriction(is_owner)
    @doc.hidden
    async def status(
        ctx: Circumstances,
        activity: Choice[Literal['playing', 'watching', 'listening', 'streaming', 'reset']],
        *, name: str = '', url: Optional[str] = None,
    ):
        if activity != 'reset' and not name:
            raise doc.NotAcceptable('Activity name cannot be empty.')
        await set_presence(activity, name=name, url=url)
        return await ctx.response(ctx).success().run()


def define_errors():
    from .ext.autodoc import exceptions
    from .ext.types.patterns import (InvalidChoices, InvalidRange,
                                     RegExpMismatch)

    add_error_names(
        exceptions.NotAcceptable,
        'HTTP 400 Bad Request',
        "That ain't it chief.",
        'Nope.',
        "Can't do that.",
    )
    add_error_names(
        exceptions.ReplyRequired,
        'Do the reply thing.',
    )
    add_error_names(
        errors.CommandOnCooldown,
        'HTTP 503 Service Unavailable',
        'Slow down please.',
        'Calm down satan.',
        'Not so fast.',
    )
    add_error_names(
        errors.MaxConcurrencyReached,
        'HTTP 503 Service Unavailable',
        'Too much work to do!',
        'The line is busy.',
    )
    add_error_names(
        (errors.CheckFailure,
         errors.CheckAnyFailure,
         errors.MissingAnyRole,
         errors.MissingRole,
         errors.MissingPermissions,
         acl.ACLFailure,
         cog.ModuleDisabled),
        'HTTP 403 Forbidden',
        'You Shall Not Pass.',
        "Sorry, you can't do that in here.",
        'Nope.',
        'Nah.',
        'Not a chance.',
        "Don't even think about it.",
    )
    add_error_names(
        (errors.BotMissingAnyRole,
         errors.MissingRole),
        'Where my roles at??',
    )
    add_error_names(
        (errors.BotMissingPermissions,
         Forbidden),
        'Where my perms at??',
    )
    add_error_names(
        errors.MissingRequiredArgument,
        'Not quite there.',
        'Not quite yet.',
        'Almost there...',
    )
    add_error_names(
        errors.TooManyArguments,
        "That's too much stuff.",
    )
    add_error_names(
        (errors.BadArgument,
         errors.BadInviteArgument,
         errors.BadBoolArgument,
         errors.BadColourArgument,
         errors.BadUnionArgument,
         RegExpMismatch,
         InvalidRange,
         InvalidChoices,
         NotFound),
        'HTTP 400 Bad Request',
        "That ain't it chief.",
        'What?',
    )
    add_error_names(
        (errors.MessageNotFound,
         errors.MemberNotFound,
         errors.UserNotFound,
         errors.ChannelNotFound,
         errors.RoleNotFound,
         errors.EmojiNotFound,
         errors.PartialEmojiConversionFailure,
         errors.CommandNotFound),
        'HTTP 404 Not Found',
        'Must be my imagination ...',
        "Must've been the wind ...",
        'What is that?',
        'You lost?',
        "I don't know what you are talking about.",
    )
    add_error_names(
        errors.ChannelNotReadable,
        'Let me in!',
    )
    add_error_names(
        errors.NSFWChannelRequired,
        'Yikes.',
    )
    add_error_names(
        Exception,
        'Oh no!',
        'Oopsie!',
        'Aw, snap!',
    )
