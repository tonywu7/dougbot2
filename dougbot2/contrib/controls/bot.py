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


from typing import Literal, Optional

from discord import Activity, ActivityType
from discord.ext.commands import (command, group, has_guild_permissions,
                                  is_owner)

from dougbot2.cog import Gear
from dougbot2.context import Circumstances
from dougbot2.exts import autodoc as doc
from dougbot2.utils.converters import Choice
from dougbot2.utils.markdown import code, escape_markdown, strong


class Controls(
    Gear, name='Control panel', order=101,
    description='Manage bot settings.',
):
    @group('prefix', invoke_without_command=True)
    @doc.description('Get the command prefix for the bot in this server.')
    @doc.invocation((), 'Print the prefix.')
    async def get_prefix(self, ctx: Circumstances):
        prefix = escape_markdown(ctx.server.prefix)
        example = f'Example: {strong(f"{prefix}help")}'
        await ctx.send(f'Prefix is {strong(prefix)}\n{example}')

    @get_prefix.command('set')
    @doc.description('Set a new prefix for this server.')
    @doc.argument('prefix', 'The new prefix to use. Spaces will be trimmed.')
    @doc.example('?', f'Set the command prefix to {code("?")}')
    @doc.restriction(has_guild_permissions, manage_guild=True)
    async def set_prefix(self, ctx: Circumstances, prefix: str):
        try:
            await ctx.server.async_set_prefix(prefix)
            await self.bot.get_prefix(ctx)
        except ValueError as e:
            await ctx.send(f'{strong("Error:")} {e}')
            raise

    async def set_presence(self, kind: str, **kwargs):
        """Set the bot's presence and persist it in the redis cache."""
        bot = self.bot
        set_presence = bot.options.get('set_presence', True)
        if not set_presence:
            return
        if kind == 'reset':
            await bot.change_presence(activity=None)
            bot.del_cache(type=f'{__name__}.activity')
            return
        try:
            presence_t = getattr(ActivityType, kind)
        except AttributeError:
            return
        activity = Activity(type=presence_t, **kwargs)
        bot.set_cache((kind, kwargs), None, type=f'{__name__}.activity')
        await bot.change_presence(activity=activity)

    async def resume_presence(self):
        """Restore the bot's presence if one is found in the cache."""
        bot = self.bot
        set_presence = bot.options.get('set_presence', True)
        if not set_presence:
            return
        kind, kwargs = bot.get_cache((None, None), type=f'{__name__}.activity')
        if kind is None:
            return await self.set_presence('reset')
        await self.set_presence(kind, **kwargs)

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
        return await ctx.response(ctx).success().run()
