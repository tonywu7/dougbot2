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

from typing import Optional

from discord import TextChannel
from discord.ext.commands import command

from ts2.discord.cog import Gear
from ts2.discord.context import Circumstances
from ts2.discord.ext import autodoc as doc


class Poll(
    Gear, name='Poll', order=20,
    description='Suggestions & polls',
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @command('suggest')
    @doc.description('Make a suggestion.')
    @doc.argument('category', 'The suggestion channel to use.')
    @doc.argument('suggestion', 'Your suggestion here.')
    async def suggest(
        self, ctx: Circumstances,
        category: Optional[TextChannel],
        *, suggestion: Optional[str],
    ):
        pass
