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

from __future__ import annotations

import logging
import os
from typing import List, Optional, Union

import psutil
from discord import (
    CategoryChannel, Member, Role, StageChannel, TextChannel, VoiceChannel,
)
from discord.ext.commands import (
    Converter, Greedy, has_guild_permissions, is_owner,
)
from discord.utils import escape_markdown
from more_itertools import split_before

from ... import documentation as doc
from ...bot import Robot
from ...command import instruction
from ...context import Circumstances
from ...converters import PermissionName
from ...extension import Gear
from ...utils.models import HypotheticalMember, HypotheticalRole
from ...utils.textutil import E, code, strong, tag, traffic_light


class LoggingLevel(Converter):
    async def convert(self, ctx: Circumstances, arg: str) -> int | str:
        level = logging.getLevelName(arg)
        if isinstance(level, int):
            return level
        return arg


class Utilities(Gear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @instruction('channels')
    @doc.description('List all channels in the server.')
    @doc.restriction(has_guild_permissions, manage_channels=True)
    async def channels(self, ctx: Circumstances, *, args: str = None):
        lines = []
        for cs in split_before(Robot.channels_ordered_1d(ctx.guild),
                               lambda c: isinstance(c, CategoryChannel)):
            if cs[0]:
                lines.append(strong(escape_markdown(cs[0].name)))
            for c in cs[1:]:
                lines.append(tag(c))
        await ctx.send('\n'.join(lines))

    @instruction('roles')
    @doc.description('List all roles in the server, including the color codes.')
    @doc.restriction(has_guild_permissions, manage_roles=True)
    async def roles(self, ctx: Circumstances, *, args: str = None):
        lines = []
        for r in reversed(ctx.guild.roles):
            lines.append(f'{tag(r)} {code(f"#{r.color.value:06x}")}')
        await ctx.send('\n'.join(lines))

    @instruction('perms')
    @doc.description('Survey role permissions.')
    @doc.argument('permission', (
        'The permission to check. Must be exactly one of the items listed under '
        '[the Discord.py documentation.](https://discordpy.readthedocs.io/en/stable/api.html#discord.Permissions)'
    ))
    @doc.argument('roles', 'The role or member whose perms to check.')
    @doc.argument('channel', 'Check the perms in the context of this channel. If not supplied, check server perms.')
    @doc.invocation(('permission',), 'Check for all roles whether a role has this permission server-wide.')
    @doc.invocation(('permission', 'channel'), 'Check for all roles whether a role has this permission in a particular channel.')
    @doc.invocation(('permission', 'roles'), 'Check if these roles have this permission server-wide.')
    @doc.invocation(('permission', 'roles', 'channel'), (
        'Check if these roles have this permission in a channel, '
        'and if someone with all these roles combined will have this permission.'
    ))
    @doc.restriction(has_guild_permissions, manage_roles=True, manage_channels=True)
    @doc.example('administrator', f'See which roles have the {code("administrator")} perm.')
    @doc.example('send_messages #rules', 'See which roles can send messages in the #rules channel.')
    @doc.example('mention_everyone @everyone @Moderator',
                 'See whether @everyone and the Moderator role has the "Mention @everyone, @here, and All Roles" perm.')
    async def perms(self, ctx: Circumstances, permission: PermissionName, roles: Greedy[Union[Role, Member]],
                    channel: Optional[Union[TextChannel, VoiceChannel, StageChannel]] = None):
        lines = []
        if roles:
            roles = {r: None for r in roles}.keys()
        subjects = roles or reversed(ctx.guild.roles)

        def unioned(subjects: List[Union[Role, Member]], cls):
            s = cls(*subjects)
            union = ' | '.join([tag(s) for s in subjects])
            return f'{traffic_light(permission(s, channel))} {union}'

        if channel:
            lines.append(f'Permission: {strong(permission.perm_name)} in {tag(channel)}')
            for r in subjects:
                s = HypotheticalMember(r)
                lines.append(f'{traffic_light(permission(s, channel))} {tag(r)}')
            if len(roles) > 1:
                lines.append(unioned(subjects, HypotheticalMember))
        else:
            lines.append(f'Permission: {strong(permission.perm_name)}')
            for r in subjects:
                lines.append(f'{traffic_light(permission(r))} {tag(r)}')
            if len(roles) > 1:
                lines.append(unioned(subjects, HypotheticalRole))

        await ctx.send('\n'.join(lines))

    @instruction('log')
    @doc.description("Put a message in the bot's log file.")
    @doc.argument('level', f'{code("logging")} levels e.g. {code("INFO")}.')
    @doc.argument('text', 'The message to log.')
    @doc.restriction(is_owner)
    async def _log(self, ctx: Circumstances, level: Optional[LoggingLevel] = None, *, text: str = ''):
        if isinstance(level, str):
            trimmed = f'{level} {text}'
            level = logging.INFO
        elif level is None:
            level = logging.INFO
        if not trimmed:
            msg = ctx.message.content
        else:
            msg = trimmed
        await ctx.log.log(f'{self.app_label}.log', level, msg)

    @instruction('throw')
    @doc.description('Throw an exception inside the command handler.')
    @doc.restriction(is_owner)
    async def _throw(self, ctx: Circumstances, *, args: str = None):
        return {}[None]

    @instruction('overflow')
    @doc.description(f'Throw a {code("RecursionError")}.')
    @doc.restriction(is_owner)
    async def _overflow(self, ctx: Circumstances, *, args: str = None):
        return await self._overflow(ctx, args=args)

    @instruction('kill')
    @doc.description('Try to kill the bot by attempting an irrecoverable stack overflow.')
    @doc.argument('sig', f'If equals {code(-9)}, {strong("send SIGKILL instead")} {E("gun")}.')
    @doc.restriction(is_owner)
    async def _kill(self, ctx: Circumstances, *, sig: str = None):
        async with ctx.typing():
            if sig == '-9':
                psutil.Process(os.getpid()).kill()
            return await self._do_kill(ctx, sig)

    async def _do_kill(self, ctx, *args, **kwargs):
        return await self._do_kill(ctx, *args, **kwargs)
