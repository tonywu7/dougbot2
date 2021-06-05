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
from datetime import datetime, timezone

from discord import Message
from discord.ext.commands import Bot, Context

from .utils.messages import trimmed_msg


class Telescope(Bot):
    def __init__(self, *, loop: asyncio.AbstractEventLoop = None, **options):
        super().__init__(loop=loop, **options)
        self.log = logging.getLogger('telescope')

        self.event(self.on_ready)
        register_all(self)

    async def on_ready(self):
        self.log.info('Bot ready')
        self.log.info(f'User {self.user}')


def register_all(bot: Bot):

    @bot.command('echo')
    async def cmd_echo(ctx: Context, *args):
        trimmed = trimmed_msg(ctx)
        if not trimmed:
            await ctx.send(ctx.message.content)
        else:
            await ctx.send(trimmed)

    @bot.command('ping')
    async def cmd_ping(ctx: Context, *args):
        await ctx.send(f':PONG {datetime.now(timezone.utc).timestamp():.6f}')

    @bot.listen('on_message')
    async def on_ping(msg: Message):
        gateway_dst = datetime.now(timezone.utc).timestamp()

        if not bot.user:
            return
        if bot.user.id != msg.author.id:
            return
        if msg.content[:6] != ':PONG ':
            return

        msg_created = msg.created_at.replace(tzinfo=timezone.utc).timestamp()

        gateway_latency = 1000 * (gateway_dst - msg_created)
        edit_start = datetime.now(timezone.utc)
        await msg.edit(content=f'Gateway (http send -> gateway receive time): {gateway_latency:.3f}ms')
        edit_latency = (datetime.now(timezone.utc) - edit_start).total_seconds()

        await msg.edit(content=f'Gateway: `{gateway_latency:.3f}ms`\nHTTP API (Edit): `{edit_latency:.3f}ms`')
