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
from typing import Any, Callable, Optional

import aiohttp
from asgiref.sync import sync_to_async
from discord import Forbidden, Game, Guild, Intents, Message
from discord.ext.commands import Bot, CommandInvokeError, CommandNotFound
from django.conf import settings
from django.core.cache import caches

from .blueprints import _MissionControl
from .defaults import get_defaults
from .discord import Circumstances
from .exts.autodoc import Manual
from .exts.errorfluff import Errorfluff
from .exts.firewall import Firewall
from .exts.papertrail import Papertrail
from .models import Server
from .utils.async_ import async_get_or_create
from .utils.duckcord import Color2, Embed2
from .utils.importutil import get_submodule_from_apps


async def _which_prefix(bot: Bot, msg: Message):
    """Find and return the prefix found in this message, if any."""
    if msg.guild is None:
        return ""
    guild_id = msg.guild.id

    @sync_to_async
    def get():
        return Server.objects.get(pk=guild_id).prefix

    try:
        prefix = await get()
        content: str = msg.content
        if content.lower().startswith(prefix.lower()):
            return content[: len(prefix)]
        return "\x00"
    except Server.DoesNotExist:
        return "\x00"


class Robot(Bot, _MissionControl):
    """Subclass of `discord.ext.commands.Bot` with aiohttp and custom method overrides."""

    _CACHE_VERSION = 2

    def __init__(self, *, loop: asyncio.AbstractEventLoop = None, **options):
        self._cache = caches["discord"]

        self.log = logging.getLogger("discord.bot")
        self.options = options

        options["allowed_mentions"] = get_defaults().default.mentions
        options["command_prefix"] = _which_prefix
        options["help_command"] = None

        intents = Intents.all()
        intents.typing = False
        intents.presences = False

        options.setdefault("intents", intents)
        options.setdefault("case_insensitive", True)
        options.setdefault("strip_after_prefix", True)
        super().__init__(loop=loop, **options)

        self._deferred_init: list[Callable[[], None]] = []

        self._autodoc = Manual()
        self._errorfluff = Errorfluff()
        self._firewall = Firewall()
        self._papertrail = Papertrail()

        self.add_cog(self._firewall)

        self._load_apps()
        self._run_deferred_initializers()

    def _load_apps(self) -> None:
        """Load all cogs from the bot's Django app config."""
        for app, module in get_submodule_from_apps("loader"):
            self.log.info(f"Loading app {app.name}")
            self.load_extension(module.__name__)

    def _run_deferred_initializers(self) -> None:
        callbacks = self._deferred_init
        while callbacks:
            callbacks.pop()()

    def dispatch(self, event_name: str, *args: Any, **kwargs: Any) -> None:
        """Override event dispatching.

        Pass the event through Gatekeeper before dispatching it.
        """
        task = asyncio.create_task(
            self._firewall.intercept(event_name, *args, **kwargs)
        )

        def callback(task: asyncio.Task):
            try:
                should_dispatch = task.result()
            except Exception:
                pass
            else:
                if not should_dispatch:
                    self.log.debug(f"Event {event_name} dropped: {args}, {kwargs}")
                    return
            return super(type(self), self).dispatch(event_name, *args, **kwargs)

        task.add_done_callback(callback)

    async def get_context(self, message: Message) -> Circumstances:
        """Override context creation.

        Use the custom `Circumstances` class, ensure server profile exists in
        database for this guild, and prevent hidden commands from running.
        """
        ctx: Circumstances = await super().get_context(message, cls=Circumstances)
        await ctx.init()
        if ctx.command and ctx.command.hidden:
            ctx.command = None
        return ctx

    async def invoke(self, ctx: Circumstances):
        """Override command invocation.

        Run post command checks, check if the command ran successfully,
        and check if subcommands did indeed run.

        Rollback the database
        transaction for the current execution if it is deemed unsuccessful
        so that no change to data is made.
        """
        await super().invoke(ctx)
        await self.on_command_returned(ctx)

    async def on_command_returned(self, ctx: Circumstances):
        """Run errands when command finishes running in invoke().

        Check if subcommands did run (via property in `Circumstances`).
        """
        if ctx.subcommand_not_completed:
            await ctx.command.dispatch_error(ctx, CommandNotFound())

    async def _init_client_session(self):
        """Start an `aiohttp.ClientSession` and keep it alive with the bot."""
        if hasattr(self, "_request"):
            await self._request.close()
        self._request = aiohttp.ClientSession(
            loop=asyncio.get_running_loop(),
            headers={"User-Agent": settings.USER_AGENT},
        )
        self.log.info("Started an aiohttp.ClientSession")

    async def before_identify_hook(self, shard_id, *, initial=False):
        """Override event before IDENTIFY.

        Run aiohttp init.
        """
        await self._init_client_session()
        return await super().before_identify_hook(shard_id, initial=initial)

    async def on_ready(self):
        """Indicate when bot is ready."""
        self.log.info("Bot is ready")
        self.log.info(f"User {self.user}")

    async def on_message(self, message: Message):
        """Override default message handler.

        Catch exceptions raised in handler but outside of command invocation,
        consider them command invoke errors, and handle them.
        """
        try:
            return await super().on_message(message)
        except Exception as exc:
            if message.author.bot:
                raise
            exc = CommandInvokeError(exc)
            ctx = await self.get_context(message)
            return await self.on_command_error(ctx, exc)

    async def on_command_error(self, ctx: Circumstances, exc: Exception) -> None:
        """Override default command error handler.

        Reply with a friendly explanation on why the command failed,
        and log the error.
        """
        await self._papertrail.log_exception(ctx, exc)
        if not (error := await self._errorfluff.get_error(ctx, exc)):
            return
        embed = Embed2(**error, color=Color2.red())
        autodelete = max([20, len(error) / 10])
        try:
            await ctx.send(embed=embed, delete_after=autodelete)
        except Forbidden:
            await ctx.send(content=str(embed), delete_after=autodelete)
        except Exception as exc:
            exc = CommandInvokeError(exc)
            await self._papertrail.log_exception(ctx, exc)

    async def _ensure_server(self, guild: Guild):
        await async_get_or_create(
            Server,
            defaults={
                "snowflake": guild.id,
                "prefix": get_defaults().default.prefix,
            },
            snowflake=guild.id,
        )

    async def on_guild_available(self, guild: Guild):
        await self._ensure_server(guild)

    def get_cache_key(self, **keys):
        """Format a prefixed string to be used as a redis cache key."""
        args = [f"{k}={v}" for k, v in keys.items()]
        return ":".join([__name__, "cache", *args])

    def get_cache(self, default=None, /, **keys):
        """Retrieve a value from the redis cache."""
        return self._cache.get(self.get_cache_key(**keys), default, self._CACHE_VERSION)

    def set_cache(self, value, ttl: Optional[float], /, **keys):
        """Set a value in the redis cache."""
        key = self.get_cache_key(**keys)
        self._cache.set(key, value, timeout=ttl, version=self._CACHE_VERSION)

    def del_cache(self, **keys):
        """Invalidate a value in the redis cache."""
        key = self.get_cache_key(**keys)
        self._cache.delete(key, version=self._CACHE_VERSION)

    async def set_exit_status(self):
        """Set the bot's presence to indicate that the bot is about to shutdown."""
        await self.change_presence(activity=Game("System Restart. Please hold."))
        self.log.info("Exit indicator is set!")

    def get_web_client(self) -> aiohttp.ClientSession:
        if not hasattr(self, "_request"):
            raise RuntimeError("Client session has not been created.")
        return self._request

    def get_option(self, key: str, default=None):
        return self.options.get(key, default)

    def defer_init(self, callback: Callable[[], None]) -> None:
        self._deferred_init.append(callback)

    @property
    def manpage(self):
        return self._autodoc

    @property
    def errorpage(self):
        return self._errorfluff

    @property
    def console(self):
        return self._papertrail
