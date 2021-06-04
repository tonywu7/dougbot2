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

from discord.ext import commands
from discord.ext.commands import Bot, Context

from .utils.messages import trimmed_msg


class Telescope(Bot):
    def __init__(self, *, loop: asyncio.AbstractEventLoop = None, **options):
        super().__init__(loop=loop, **options)
        self.log = logging.getLogger('telescope')

        self.event(self.on_ready)
        self.add_command(self.cmd_echo)

    async def on_ready(self):
        self.log.info('Bot ready')
        self.log.info(f'User {self.user}')

    @commands.command('echo')
    async def cmd_echo(ctx: Context, *args):
        trimmed = trimmed_msg(ctx)
        if not trimmed:
            await ctx.send(ctx.message.content)
        else:
            await ctx.send(trimmed)
