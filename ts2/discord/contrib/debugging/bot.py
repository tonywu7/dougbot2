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
import os
from typing import Literal, Optional, Union

import psutil
from discord import Member, Role, TextChannel
from discord.ext.commands import (BucketType, Converter, command, has_role,
                                  is_owner)

from ts2.discord.cog import Gear
from ts2.discord.context import Circumstances
from ts2.discord.ext.common import Constant, doc
from ts2.discord.utils.markdown import E, a, code, strong


class LoggingLevel(Converter):

    async def convert(self, ctx: Circumstances, arg: str) -> int | str:
        """Convert a logging level name (e.g. DEBUG) to its int value."""
        level = logging.getLevelName(arg)
        if isinstance(level, int):
            return level
        return arg


class Debugging(
    Gear, name='Debugging', order=95,
    description='',
):
    """Cog for internal debugging commands."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @command('stderr')
    @doc.description("Send a message into the bot's log file.")
    @doc.argument('level', f'{code("logging")} levels e.g. {code("INFO")}.')
    @doc.argument('text', 'The message to log.')
    @doc.restriction(is_owner)
    @doc.hidden
    async def _log(self, ctx: Circumstances, level: Optional[LoggingLevel] = None, *, text: str = ''):
        if isinstance(level, str):
            text = f'{level} {text}'
            level = logging.INFO
        elif level is None:
            level = logging.INFO
        if not text:
            msg = ctx.message.content
        else:
            msg = text
        await ctx.log.log(f'{self.app_label}.log', level, msg)

    @command('throw')
    @doc.description('Throw an exception inside the command handler.')
    @doc.restriction(is_owner)
    @doc.cooldown(1, 10, BucketType.user)
    @doc.hidden
    async def _throw(self, ctx: Circumstances, *, args: str = None):
        return {}[None]

    @command('overflow')
    @doc.description(f'Throw a {code("RecursionError")}.')
    @doc.restriction(is_owner)
    @doc.hidden
    async def _overflow(self, ctx: Circumstances, *, args: str = None):
        return await self._overflow(ctx, args=args)

    @command('kill')
    @doc.description('Try to kill the bot by attempting an irrecoverable stack overflow.')
    @doc.argument('sig', f'If equals {code(-9)}, {strong("send SIGKILL instead")} {E("gun")}.')
    @doc.restriction(is_owner)
    @doc.hidden
    async def _kill(self, ctx: Circumstances, *, sig: str = None):
        async with ctx.typing():
            if sig == '-9':
                psutil.Process(os.getpid()).kill()
            return await self._do_kill(ctx, sig)

    async def _do_kill(self, ctx, *args, **kwargs):
        return await self._do_kill(ctx, *args, **kwargs)

    @command('sleep')
    @doc.description('Suspend the handler coroutine for some duration.')
    @doc.concurrent(2, BucketType.user, wait=False)
    @doc.hidden
    async def _sleep(self, ctx: Circumstances, duration: Optional[float] = 10):
        async with ctx.typing():
            await asyncio.sleep(duration)

    @command('isnotinthesudoersfile')
    @doc.description('[Incident](https://xkcd.com/838/)')
    @doc.restriction(has_role, item=0)
    @doc.hidden
    async def _sudo(self, ctx: Circumstances, *, args: str = None):
        await ctx.send(f'{ctx.me} is in the sudoers file!')

    @command('444')
    @doc.description('Globally forbid an entity from interacting with the bot.')
    @doc.discussion('Detail', (
        f'All command invocations are ignored and all events (including {code("on_message")})'
        " are silently dropped.\nThe name of this command comes from nginx's"
        f' {a("HTTP 444", "https://en.wikipedia.org/wiki/List_of_HTTP_status_codes#nginx")}'
        ' status code.'
    ))
    @doc.restriction(is_owner)
    @doc.hidden
    async def _blacklist(self, ctx: Circumstances, entity: Union[Member, Role, TextChannel],
                         free: Optional[Constant[Literal['free']]]):
        if free:
            await ctx.bot.gatekeeper.discard(entity)
        else:
            await ctx.bot.gatekeeper.add(entity)
