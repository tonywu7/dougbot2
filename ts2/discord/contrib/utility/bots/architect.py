# architect.py
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

from typing import Any, Literal

from discord import Activity, ActivityType
from discord.ext.commands import command, is_owner

from ts2.discord.bot import Robot
from ts2.discord.cog import Gear
from ts2.discord.context import Circumstances
from ts2.discord.ext import autodoc as doc
from ts2.discord.ext.common import Choice


class BotConfigCommands:
    bot: Robot

    @Gear.listener('on_connect')
    async def resume_presence(self):
        kind, kwargs = self.bot.get_cache((None, None), type=f'{__name__}.activity')
        if kind is None:
            return
        await self.set_presence(kind, **kwargs)

    async def set_presence(self, kind: str, **kwargs):
        try:
            presence_t = getattr(ActivityType, kind)
        except AttributeError:
            return
        activity = Activity(type=presence_t, **kwargs)
        self.bot.set_cache((kind, kwargs), None, type=f'{__name__}.activity')
        await self.bot.change_presence(activity=activity)

    @command('status')
    @doc.description("Change the bot's status.")
    @doc.argument('activity', 'The type of activity.')
    @doc.argument('name', 'The description of the status.')
    @doc.restriction(is_owner)
    @doc.hidden
    async def status(
        self, ctx: Circumstances,
        activity: Choice[Literal['playing', 'watching', 'listening', 'streaming']],
        *, name: str, **kwargs: Any,
    ):
        await self.set_presence(activity, name=name, **kwargs)
