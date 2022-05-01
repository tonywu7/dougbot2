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

from contextlib import asynccontextmanager
from datetime import timezone
from typing import Optional

from discord import File
from discord.ext.commands import Command, Context, Group

from ..blueprints import _Surroundings
from ..defaults import get_defaults
from ..utils.async_ import async_get_or_create
from ..utils.common import Embed2, ResponseInit, is_direct_message
from .command import CommandDelegate, GroupDelegate


# 'Cause of ...
class Circumstances(Context, _Surroundings):
    """Subclass of `discord.ext.commands.Context` providing common convenient methods."""

    def __init__(self, **attrs):
        super().__init__(**attrs)
        self.timestamp = self.message.created_at.replace(tzinfo=timezone.utc)
        self.styles = get_defaults().styles

    async def init(self):
        from ..models import Server
        if not self.guild:
            return
        self._server = await async_get_or_create(Server, defaults={
            'snowflake': self.guild.id,
            'prefix': get_defaults().default.prefix,
        }, snowflake=self.guild.id)

    @property
    def subcommand_not_completed(self):
        cmd = self.command
        if isinstance(cmd, (CommandDelegate, GroupDelegate)):
            cmd = cmd.unwrap()
        return isinstance(cmd, Group) and not cmd.invoke_without_command

    @property
    def command(self) -> Optional[Command]:
        """Return the current Command if any."""
        return self._command

    @command.setter
    def command(self, cmd):
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
        if isinstance(cmd, Group):
            self._invoked_subcommand = GroupDelegate(cmd)
        elif isinstance(cmd, Command):
            self._invoked_subcommand = CommandDelegate(cmd)
        else:
            self._invoked_subcommand = cmd

    @property
    def full_invoked_with(self) -> str:
        """The fully-qualified sequence of command names that has been parsed."""
        return ' '.join({
            **{k: True for k in self.invoked_parents},
            self.invoked_with: True,
        }.keys())

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

    def respond(
        self, content: Optional[str] = None,
        embed: Optional[Embed2] = None,
        files: Optional[list[File]] = None,
        nonce: Optional[int] = None,
    ) -> ResponseInit:
        return ResponseInit(self, content, embed, files, nonce)

    def get_logger(self):
        cmd = self.full_invoked_with.replace(' ', '.')
        return self.bot.console.get_logger(f'discord.cmd.{cmd}', self.guild)

    async def call(self, cmd: Command, *args, **kwargs):
        """Invoke an arbitrary command but with concurrency and cooldowns triggered."""
        async with self.concurrently(cmd):
            self.set_cooldown(cmd)
            return await self.invoke(cmd, *args, **kwargs)

    def set_cooldown(self, cmd: Command):
        """Manually trigger the cooldown rules for this command."""
        cmd._prepare_cooldowns(self)

    @asynccontextmanager
    async def concurrently(self, cmd: Command):
        """Manually trigger the concurrency rules for this command."""
        try:
            if cmd._max_concurrency is not None:
                await cmd._max_concurrency.acquire(self)
            yield
        finally:
            if cmd._max_concurrency is not None:
                await cmd._max_concurrency.release(self)
