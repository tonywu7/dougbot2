# context.py
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
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager, suppress
from datetime import timezone
from functools import wraps
from typing import Optional, Union

from asgiref.sync import sync_to_async
from discord import Forbidden, Guild, Member, Message, TextChannel, User
from discord.abc import Messageable
from discord.ext.commands import Command, Context, Group
from discord.ext.commands.errors import CommandInvokeError
from django.db import transaction

from .command import CommandDelegate, GroupDelegate
from .models import Server
from .utils.common import Embed2, Responder, ResponseInit, is_direct_message


def on_error_reset_cooldown(f):
    """Wrap a command callback such that command cooldowns are reset if the command raises."""
    @wraps(f)
    async def wrapper(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except Exception:
            if isinstance(args[0], Context):
                ctx = args[0]
            else:
                ctx = args[1]
            ctx.command.reset_cooldown(ctx)
            raise
    return wrapper


# 'Cause of ...
class Circumstances(Context):
    """Subclass of `discord.ext.commands.Context` providing common convenient methods."""

    send: Callable[..., Coroutine[None, None, Message]]
    reply: Callable[..., Coroutine[None, None, Message]]

    def __init__(self, **attrs):
        from .bot import Robot

        self.command_searched = {}
        self.command_materialized = {}

        super().__init__(**attrs)
        self._server: Server

        self.me: Union[Member, User]
        self.message: Union[Message, Messageable]
        self.invoked_with: str
        self.invoked_parents: list[str]
        self.invoked_subcommand: Optional[Command]

        self.author: Union[Member, Messageable]
        self.guild: Guild
        self.channel: TextChannel

        self.bot: Robot
        self.prefix: str

        self.session = self.bot.request
        self.response = ResponseInit

        self.timestamp = self.message.created_at.replace(tzinfo=timezone.utc)

    @property
    def subcommand_not_completed(self):
        # TODO: Deprecate
        cmd = self.command
        if isinstance(cmd, (CommandDelegate, GroupDelegate)):
            cmd = cmd.unwrap()
        return isinstance(cmd, Group) and not cmd.invoke_without_command

    @property
    def materialized_path(self) -> str:
        # TODO: Deprecate
        return ' '.join(self.command_materialized)

    @property
    def searched_path(self) -> str:
        # TODO: Use full_invoked_with + subcommand_passed instead
        return ' '.join(self.command_searched)

    @property
    def command(self) -> Optional[Command]:
        """Return the current Command if any."""
        return self._command

    @command.setter
    def command(self, cmd):
        # TODO: Will deprecate
        self._path_append(cmd)
        # Wrap native Command objects around a delegate mixin
        # in order to intercept attribute access for further customization.
        if isinstance(cmd, Group):
            self._command = GroupDelegate(cmd)
        elif isinstance(cmd, Command):
            self._command = CommandDelegate(cmd)
        else:
            self._command = cmd

    @property
    def invoked_subcommand(self) -> Optional[Command]:
        """Return the final subcommand to be invoked, if any."""
        return self._invoked_subcommand

    @invoked_subcommand.setter
    def invoked_subcommand(self, cmd: Optional[Command]):
        # TODO: Will deprecate
        self._path_append(cmd)
        if isinstance(cmd, Group):
            self._invoked_subcommand = GroupDelegate(cmd)
        elif isinstance(cmd, Command):
            self._invoked_subcommand = CommandDelegate(cmd)
        else:
            self._invoked_subcommand = cmd

    @property
    def subcommand_passed(self) -> str:
        # TODO: Deprecate
        return self._subcommand_passed

    @subcommand_passed.setter
    def subcommand_passed(self, cmd: str):
        # TODO: Deprecate
        self._path_append(cmd)
        self._subcommand_passed = cmd

    def _path_append(self, cmd: Optional[Union[str, Command]]):
        # TODO: Deprecate
        if isinstance(cmd, Command):
            for alias in cmd.aliases:
                self.command_searched.pop(alias, None)
            self.command_searched[cmd.name] = cmd
            self.command_materialized[cmd.name] = cmd
        elif isinstance(cmd, str):
            self.command_searched[cmd] = None

    @property
    def full_invoked_with(self) -> str:
        """The fully-qualified sequence of command names that has been parsed."""
        return ' '.join({**{k: True for k in self.invoked_parents},
                         self.invoked_with: True}.keys())

    @property
    def raw_input(self) -> str:
        """The rest of the message content after all parsed commands."""
        msg: str = self.view.buffer
        return (msg.removeprefix(self.prefix)
                .strip()[len(self.full_invoked_with):]
                .strip())

    @property
    def is_direct_message(self):
        """Whether the current context is in a DM."""
        return is_direct_message(self.channel)

    @property
    def server(self):
        """Current guild's server profile in the database.

        :raises NotInServer: if the current guild does not have a profile
        or if the current context is not a guild context (e.g. in a DM).
        """
        try:
            return self._server
        except AttributeError:
            raise NotInServer

    @property
    def logconfig(self) -> dict:
        """Logging config for the current guild.

        Returns an empty dict if no server profile exists for this context.
        """
        try:
            return self.server.logging
        except NotInServer:
            return {}

    @property
    def log(self):
        """The `ServerLogger` attached to the current guild.

        :raises NotInServer: if the current context is not a guild context.
        """
        from .ext.logging import ServerLogger
        if not self.guild:
            raise NotInServer
        return ServerLogger('discord.logging', self.guild, self.logconfig)

    async def init(self):
        """Run Context init tasks that must be run asynchronously.

        Retrieve the server profile in database for the current guild.
        """
        await self._get_server()

    @sync_to_async
    def _get_server(self):
        from .models import Server
        try:
            self._server = (
                Server.objects
                .prefetch_related('channels', 'roles')
                .get(pk=self.message.guild.id)
            )
        except AttributeError:
            return
        except Server.DoesNotExist:
            raise

    @sync_to_async
    def set_prefix(self, prefix: str):
        # TODO: Move to bot.py
        from .models import validate_prefix
        validate_prefix(prefix)
        with transaction.atomic():
            self.server.prefix = prefix
            self.server.save()

    async def run_responders(self, *responders: Responder, ignore_exc=True):
        # TODO: Remove
        results = await asyncio.gather(*responders, return_exceptions=True)
        if ignore_exc:
            return
        for r in results:
            if isinstance(r, Exception):
                from .ext.logging import log_command_error
                log_command_error(self, self.logconfig, r)

    def format_command(self, cmd: str):
        """Prefix the string with the currently used prefix.

        Useful for recommending other commands and customizing it to the
        current guild and user.
        """
        assert cmd in self.bot.manual.commands
        return f'{self.prefix}{cmd}'

    async def send_dm_safe(self, content: Optional[str] = None,
                           embed: Optional[Embed2] = None,
                           **kwargs) -> Optional[Message]:
        """Try to send a DM and do nothing if Forbidden."""
        with suppress(Forbidden):
            return await self.author.send(content=content, embed=embed, **kwargs)

    async def send_help(self, query: str = None):
        """Send help info for the current command or for another command."""
        query = query or self.command.qualified_name
        return await self.bot.manual.do_help(self, query)

    async def call(self, cmd: Command, *args, **kwargs):
        """Invoke an arbitrary command but with concurrency and cooldowns triggered."""
        async with self.acquire_concurrency(cmd):
            self.trigger_cooldowns(cmd)
            return await self.invoke(cmd, *args, **kwargs)

    @asynccontextmanager
    async def acquire_concurrency(self, cmd: Command):
        """Manually trigger the concurrency rules for this command."""
        try:
            if cmd._max_concurrency is not None:
                await cmd._max_concurrency.acquire(self)
            yield
        finally:
            if cmd._max_concurrency is not None:
                await cmd._max_concurrency.release(self)

    def trigger_cooldowns(self, cmd: Command):
        """Manually trigger the cooldown rules for this command."""
        cmd._prepare_cooldowns(self)


class NotInServer(CommandInvokeError, AttributeError):
    def __init__(self):
        super().__init__('Context is missing server instance.')
