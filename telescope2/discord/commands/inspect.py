# inspect.py
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

from typing import Callable, List, Optional, Union, overload

from discord import (CategoryChannel, Member, Permissions, Role, StageChannel,
                     TextChannel, VoiceChannel)
from discord.abc import GuildChannel
from discord.ext.commands import BadArgument, Bot, Converter, Greedy
from discord.utils import escape_markdown
from more_itertools import split_before

from ..bot import Circumstances, Robot
from ..utils.constructs import HypotheticalMember, HypotheticalRole
from ..utils.messages import color_to_rgb8, tag, traffic_light


class PermissionTest(Converter):
    perm_name: str

    async def convert(self, ctx: Circumstances, arg: str) -> Callable[[Role], bool]:
        if not hasattr(Permissions, arg):
            raise BadArgument(
                f'No such permission {arg}\n'
                'Consult https://discordpy.readthedocs.io/'
                'en/stable/api.html#discord.Permissions '
                'for a list of possible attributed.',
            )
        self.perm_name = arg
        return self

    @overload
    def __call__(self, entity: Role, channel: None) -> bool:
        ...

    @overload
    def __call__(self, entity: Member, channel: None) -> bool:
        ...

    @overload
    def __call__(self, entity: Member, channel: GuildChannel) -> bool:
        ...

    def __call__(self, entity: Role | Member, channel: Optional[GuildChannel] = None) -> bool:
        if channel:
            return getattr(channel.permissions_for(entity), self.perm_name)
        if isinstance(entity, Member):
            entity = HypotheticalRole(*entity.roles)
        return entity.permissions.administrator or getattr(entity.permissions, self.perm_name)


def register_all(bot: Bot):

    @bot.command('channels')
    async def channels(ctx: Circumstances, *args):
        lines = []
        for cs in split_before(Robot.channels_ordered_1d(ctx.guild),
                               lambda c: isinstance(c, CategoryChannel)):
            if cs[0]:
                lines.append(f'**{escape_markdown(cs[0].name)}**')
            for c in cs[1:]:
                lines.append(tag(c))
        await ctx.send('\n'.join(lines))

    @bot.command('roles')
    async def roles(ctx: Circumstances, *args):
        lines = []
        for r in reversed(ctx.guild.roles):
            lines.append(f'{tag(r)} `#{color_to_rgb8(r.color):06x}`')
        await ctx.send('\n'.join(lines))

    @bot.command('perms')
    async def perms(ctx: Circumstances, permtest: PermissionTest, roles: Greedy[Union[Role, Member]],
                    channel: Optional[Union[TextChannel, VoiceChannel, StageChannel]] = None):
        lines = []
        subjects = roles or reversed(ctx.guild.roles)

        def unioned(subjects: List[Union[Role, Member]], cls):
            s = cls(*subjects)
            union = ' | '.join([tag(s) for s in subjects])
            return f'{traffic_light(permtest(s, channel))} {union}'

        if channel:
            lines.append(f'Permission: **{permtest.perm_name}** in {tag(channel)}')
            for r in subjects:
                s = HypotheticalMember(r)
                lines.append(f'{traffic_light(permtest(s, channel))} {tag(r)}')
            if len(roles) > 1:
                lines.append(unioned(subjects, HypotheticalMember))
        else:
            lines.append(f'Permission: **{permtest.perm_name}**')
            for r in subjects:
                lines.append(f'{traffic_light(permtest(r))} {tag(r)}')
            if len(roles) > 1:
                lines.append(unioned(subjects, HypotheticalRole))

        await ctx.send('\n'.join(lines))
