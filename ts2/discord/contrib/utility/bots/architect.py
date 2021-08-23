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

import asyncio
from typing import Literal, Optional

from discord import Activity, ActivityType
from discord.ext.commands import command, is_owner

from ts2.discord.bot import Robot
from ts2.discord.cog import Gear
from ts2.discord.context import Circumstances
from ts2.discord.ext import autodoc as doc
from ts2.discord.ext.common import Choice


class BotConfigCommands:
    bot: Robot

    @Gear.listener('on_ready')
    async def resume_presence(self):
        await asyncio.sleep(10)
        kind, kwargs = self.bot.get_cache((None, None), type=f'{__name__}.activity')
        if kind is None:
            return await self.set_presence('reset')
        await self.set_presence(kind, **kwargs)

    async def set_presence(self, kind: str, **kwargs):
        if kind == 'reset':
            await self.bot.change_presence(activity=None)
            self.bot.del_cache(type=f'{__name__}.activity')
            return
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
        activity: Choice[Literal['playing', 'watching', 'listening', 'streaming', 'reset']],
        *, name: str = '', url: Optional[str] = None,
    ):
        if activity != 'reset' and not name:
            raise doc.NotAcceptable('Activity name cannot be empty.')
        await self.set_presence(activity, name=name, url=url)
