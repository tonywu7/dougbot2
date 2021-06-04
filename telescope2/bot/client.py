# client.py
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
import multiprocessing
from typing import Type

from discord import Client
from discord.ext import commands
from discord.ext.commands import Bot, Context
from django.conf import settings


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
    async def cmd_echo(self, ctx: Context, *args):
        await ctx.send(ctx.message)


class BotProcess(multiprocessing.Process):
    def __init__(self, client_cls: Type[Client], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._client_cls = client_cls
        self._client_options = kwargs

        self.client: Client
        self.loop: asyncio.BaseEventLoop

    def run_client(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.client = self._client_cls(loop=self.loop, **self._client_options)
        self.client.run(settings.DISCORD_SECRET)

    def run(self) -> None:
        return self.run_client()
