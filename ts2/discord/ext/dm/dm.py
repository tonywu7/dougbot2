# dm.py
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

from discord import DMChannel
from discord.ext.commands import Command, Context, NoPrivateMessage

from ...utils.functional import get_memo


def is_direct_message(ctx: Context):
    return isinstance(ctx.channel, DMChannel)


async def dm_allowed_check(ctx: Context) -> bool:
    cmd: Command = ctx.command
    if not cmd:
        return True
    memo = get_memo(cmd, '__command_info__', '_callback', default={})
    if not is_direct_message(ctx) or memo.get('direct_message'):
        return True
    raise NoPrivateMessage()
