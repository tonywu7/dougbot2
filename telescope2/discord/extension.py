# extension.py
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

import logging

from discord.ext.commands import Bot, Cog
from discord.ext.commands.errors import DisabledCommand


class Gear(Cog):
    def __init__(self, label: str, bot: Bot, *args, **kwargs):
        super().__init__()
        self.bot = bot
        self.app_label = label
        self.log = logging.getLogger(f'discord.logging.ext.{label}')


async def cog_enabled_check(ctx) -> bool:
    if await ctx.bot.is_owner(ctx.author):
        return True
    extension = ctx.cog
    if not (extension is None or extension.app_label in ctx.server.extensions):
        raise ModuleDisabled(extension)
    return True


class ModuleDisabled(DisabledCommand):
    def __init__(self, cog: Cog, *args):
        super().__init__(message=f'Attempted to use disabled module {cog.qualified_name}', *args)
