# debug.py
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

from discord import Message
from discord.ext.commands import Bot, Context

from telescope2.utils import lang
from telescope2.utils.datetime import utcnow, utctimestamp

from ..utils.messages import trimmed_msg


def register_all(bot: Bot):
    @bot.command('echo')
    async def cmd_echo(ctx: Context, *args, **kwargs):
        trimmed = trimmed_msg(ctx)
        if not trimmed:
            await ctx.send(ctx.message.content)
        else:
            await ctx.send(trimmed)

    @bot.command('ping')
    async def cmd_ping(ctx: Context, *args, **kwargs):
        await ctx.send(f':PONG {utctimestamp()}')

    @bot.command('prefix')
    async def cmd_prefix(ctx: Context, *args, **kwargs):
        prefixes = [*await bot.command_prefix(bot, ctx.message)]
        example = f'Example: **{prefixes[0]}echo**'
        await ctx.send(f'{lang.plural_clause(len(prefixes), "Prefix", "is")} '
                       f'{lang.coord_conj(*[f"**{p}**" for p in prefixes])}\n'
                       f'{example}')

    @bot.listen('on_message')
    async def on_ping(msg: Message):
        gateway_dst = utctimestamp()

        if not bot.user:
            return
        if bot.user.id != msg.author.id:
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

        await msg.edit(content=f'Gateway: `{gateway_latency:.3f}ms`\nHTTP API (Edit): `{edit_latency:.3f}ms`')