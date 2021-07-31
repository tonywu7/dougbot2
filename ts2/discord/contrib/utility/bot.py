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

from collections import defaultdict
from typing import Optional, Union

import attr
from discord import (CategoryChannel, Member, Role, StageChannel, TextChannel,
                     VoiceChannel)
from discord.ext.commands import Greedy, command, has_guild_permissions
from more_itertools import split_before

from ts2.discord.bot import channels_ordered_1d
from ts2.discord.cog import Gear
from ts2.discord.context import Circumstances
from ts2.discord.ext import autodoc as doc
from ts2.discord.ext.types.models import PermissionName
from ts2.discord.utils.common import (Embed2, EmbedField, EmbedPagination,
                                      chapterize, chapterize_fields, code,
                                      strong, tag, traffic_light)
from ts2.discord.utils.models import HypotheticalMember, HypotheticalRole

PERMISSIONS = """\
(Underscores are required)

**General server permissions**
`manage_channels`, `manage_emojis`, `manage_server`,
`manage_roles`, `manage_webhooks`,
`view_audit_log`, `view_channel`, `view_guild_insights`,

**Membership permissions**
`create_instant_invite`,
`manage_nicknames`, `change_nickname`,
`kick_members`, `ban_members`,

**Text channel permissions**
`read_messages`, `send_messages`,
`attach_files`, `embed_links`,
`add_reactions`, `external_emojis`,
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


class Utilities(
    Gear, name='Utilities', order=50,
    description='',
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @command('channels')
    @doc.description('List all channels in the server.')
    @doc.restriction(has_guild_permissions, manage_channels=True)
    async def channels(self, ctx: Circumstances):
        channels: defaultdict[str, list[str]] = defaultdict(list)
        for cs in split_before(channels_ordered_1d(ctx.guild),
                               lambda c: isinstance(c, CategoryChannel)):
            first = cs[0]
            category = '(no category)'
            if first:
                if isinstance(first, CategoryChannel):
                    category = first.name
                    channels[category] = []
                else:
                    channels[category].append(tag(first))
            for c in cs[1:]:
                channels[category].append(tag(c))
        fields = [EmbedField(name=k, value='\n'.join(v), inline=False)
                  for k, v in channels.items()]
        pages: list[Embed2] = []
        base_embed = Embed2(title='Channels').decorated(ctx.guild)
        for fieldset in chapterize_fields(fields, linebreak='newline'):
            pages.append(attr.evolve(base_embed, fields=fieldset))
        pagination = EmbedPagination(pages, 'Channels', False)
        return (await ctx.response(ctx, embed=pagination.get_embed(0))
                .responder(lambda m: pagination(ctx.bot, m, 300, ctx.author))
                .run())

    @command('roles')
    @doc.description('List all roles in the server, including the color codes.')
    @doc.restriction(has_guild_permissions, manage_roles=True)
    async def roles(self, ctx: Circumstances):
        lines = []
        for r in reversed(ctx.guild.roles):
            if r.color.value:
                lines.append(f'{tag(r)} {code(f"#{r.color.value:06x}")}')
            else:
                lines.append(tag(r))
        body = '\n'.join(lines)
        sections = chapterize(body, 720, 720, closing='', opening='',
                              linebreak='newline')
        pages = [Embed2(description=c).decorated(ctx.guild) for c in sections]
        pagination = EmbedPagination(pages, 'Roles', False)
        return (await ctx.response(ctx, embed=pagination.get_embed(0))
                .responder(lambda m: pagination(ctx.bot, m, 300, ctx.author))
                .run())

    @command('perms', ignore_extra=False)
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
