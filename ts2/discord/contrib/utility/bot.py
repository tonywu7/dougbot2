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

from typing import Optional, Union

from discord import (CategoryChannel, Member, Role, StageChannel, TextChannel,
                     VoiceChannel)
from discord.ext.commands import Greedy, has_guild_permissions
from discord.utils import escape_markdown
from more_itertools import split_before

from ts2.discord import documentation as doc
from ts2.discord.bot import Robot
from ts2.discord.command import instruction
from ts2.discord.context import Circumstances
from ts2.discord.converters import PermissionName
from ts2.discord.extension import Gear
from ts2.discord.utils.markdown import code, strong, tag, traffic_light
from ts2.discord.utils.models import HypotheticalMember, HypotheticalRole


class Utilities(Gear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @instruction('channels')
    @doc.description('List all channels in the server.')
    @doc.restriction(has_guild_permissions, manage_channels=True)
    async def channels(self, ctx: Circumstances):
        lines = []
        for cs in split_before(Robot.channels_ordered_1d(ctx.guild),
                               lambda c: isinstance(c, CategoryChannel)):
            if cs[0]:
                if isinstance(cs[0], CategoryChannel):
                    lines.append(strong(escape_markdown(cs[0].name)))
                else:
                    lines.append(tag(cs[0]))
            for c in cs[1:]:
                lines.append(tag(c))
        await ctx.send('\n'.join(lines))

    @instruction('roles')
    @doc.description('List all roles in the server, including the color codes.')
    @doc.restriction(has_guild_permissions, manage_roles=True)
    async def roles(self, ctx: Circumstances):
        lines = []
        for r in reversed(ctx.guild.roles):
            lines.append(f'{tag(r)} {code(f"#{r.color.value:06x}")}')
        await ctx.send('\n'.join(lines))

    @instruction('perms', ignore_extra=False)
    @doc.description('Survey role permissions.')
    @doc.argument('permission', ('The permission to check.'))
    @doc.argument('roles', 'The role or member whose perms to check.')
    @doc.argument('channel', 'Check the perms in the context of this channel. If not supplied, check server perms.')
    @doc.invocation((), 'Show a list of possible permission names.')
    @doc.invocation(('channel',), False)
    @doc.invocation(('roles',), False)
    @doc.invocation(('roles', 'channel'), False)
    @doc.invocation(('permission',), 'Check for all roles whether a role has this permission server-wide.')
    @doc.invocation(('permission', 'channel'), 'Check for all roles whether a role has this permission in a particular channel.')
    @doc.invocation(('permission', 'roles'), 'Check if these roles have this permission server-wide.')
    @doc.invocation(('permission', 'roles', 'channel'), (
        'Check if these roles have this permission in a channel, '
        'and if someone with all these roles combined will have this permission.'
    ))
    @doc.restriction(has_guild_permissions, manage_roles=True)
    @doc.example('administrator', f'See which roles have the {code("administrator")} perm.')
    @doc.example('send_messages #rules', 'See which roles can send messages in the #rules channel.')
    @doc.example('mention_everyone @everyone @Moderator',
                 'See whether @everyone and the Moderator role has the "Mention @everyone, @here, and All Roles" perm.')
    async def perms(self, ctx: Circumstances, permission: Optional[PermissionName], roles: Greedy[Union[Role, Member]],
                    channel: Optional[Union[TextChannel, VoiceChannel, StageChannel]] = None):
        if not permission:
            return await ctx.send(PERMISSIONS)

        lines = []
        if roles:
            roles = {r: None for r in roles}.keys()
        subjects = roles or reversed(ctx.guild.roles)

        def unioned(subjects: list[Union[Role, Member]], cls):
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


PERMISSIONS = """\
(Underscores are required)

**General server permissions**
`manage_channels`, `manage_emojis`, `manage_server`,
`manage_roles`/`manage_permissions`, `manage_webhooks`,
`view_audit_log`, `view_channel`, `view_guild_insights`,

**Membership permissions**
`create_instant_invite`,
`manage_nicknames`, `change_nickname`,
`kick_members`, `ban_members`,

**Text channel permissions**
`read_messages`, `send_messages`,
`attach_files`, `embed_links`,
`add_reactions`, `external_emojis`/`use_external_emojis`,
`mention_everyone`, `manage_messages`,
`read_message_history`, `send_tts_messages`,
`use_slash_commands`,

**Voice channel permissions**
`connect`, `speak`, `stream`,
`use_voice_activation`,
`priority_speaker`,
`mute_members`, `move_members`,
`deafen_members`, `request_to_speak`,

**Privileged permission**
`administrator`
"""
