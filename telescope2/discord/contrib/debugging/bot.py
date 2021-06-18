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

import logging
import os
from typing import Optional

import psutil
from discord.ext.commands import Converter, is_owner

from ... import documentation as doc
from ...command import instruction
from ...context import Circumstances
from ...extension import Gear
from ...utils.textutil import E, code, strong


class LoggingLevel(Converter):
    async def convert(self, ctx: Circumstances, arg: str) -> int | str:
        level = logging.getLevelName(arg)
        if isinstance(level, int):
            return level
        return arg


class Debugging(Gear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @instruction('log')
    @doc.description("Put a message in the bot's log file.")
    @doc.argument('level', f'{code("logging")} levels e.g. {code("INFO")}.')
    @doc.argument('text', 'The message to log.')
    @doc.restriction(is_owner)
    async def _log(self, ctx: Circumstances, level: Optional[LoggingLevel] = None, *, text: str = ''):
        if isinstance(level, str):
            trimmed = f'{level} {text}'
            level = logging.INFO
        elif level is None:
            level = logging.INFO
        if not trimmed:
            msg = ctx.message.content
        else:
            msg = trimmed
        await ctx.log.log(f'{self.app_label}.log', level, msg)

    @instruction('throw')
    @doc.description('Throw an exception inside the command handler.')
    @doc.restriction(is_owner)
    async def _throw(self, ctx: Circumstances, *, args: str = None):
        return {}[None]

    @instruction('overflow')
    @doc.description(f'Throw a {code("RecursionError")}.')
    @doc.restriction(is_owner)
    async def _overflow(self, ctx: Circumstances, *, args: str = None):
        return await self._overflow(ctx, args=args)

    @instruction('kill')
    @doc.description('Try to kill the bot by attempting an irrecoverable stack overflow.')
    @doc.argument('sig', f'If equals {code(-9)}, {strong("send SIGKILL instead")} {E("gun")}.')
    @doc.restriction(is_owner)
    async def _kill(self, ctx: Circumstances, *, sig: str = None):
        async with ctx.typing():
            if sig == '-9':
                psutil.Process(os.getpid()).kill()
            return await self._do_kill(ctx, sig)

    async def _do_kill(self, ctx, *args, **kwargs):
        return await self._do_kill(ctx, *args, **kwargs)
