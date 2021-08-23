# surveyor.py
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

import colorsys
import io
from collections import defaultdict
from datetime import datetime, timezone
from itertools import chain
from string import hexdigits
from typing import Optional, Union

import attr
from discord import (CategoryChannel, File, Guild, Member, Message, Role,
                     StageChannel, TextChannel, VoiceChannel)
from discord.abc import GuildChannel
from discord.ext.commands import Greedy, command, has_guild_permissions
from more_itertools import collapse, first, map_reduce
from PIL import Image, ImageColor

from ts2.discord.context import Circumstances
from ts2.discord.ext import autodoc as doc
from ts2.discord.ext.types.models import PermissionName
from ts2.discord.utils.common import (Embed2, EmbedField, EmbedPagination,
                                      Permissions2, a, chapterize,
                                      chapterize_fields, code, get_total_perms,
                                      strong, tag, timestamp, traffic_light)
from ts2.discord.utils.markdown import rgba2int

PERMISSIONS = {
    'General server permissions': [
        'manage_channels', 'manage_emojis', 'manage_guild',
        'manage_roles', 'manage_webhooks',
        'view_audit_log', 'view_guild_insights',
    ],
    'Membership permissions': [
        'create_instant_invite',
        'manage_nicknames', 'change_nickname',
        'kick_members', 'ban_members',
    ],
    'Text channel permissions': [
        'read_messages', 'send_messages',
        'attach_files', 'embed_links',
        'add_reactions', 'external_emojis',
        'mention_everyone', 'manage_messages',
        'read_message_history', 'send_tts_messages',
        'use_slash_commands',
    ],
    'Voice channel permissions': [
        'connect', 'speak', 'stream',
        'use_voice_activation',
        'priority_speaker',
        'mute_members', 'move_members',
        'deafen_members', 'request_to_speak',
    ],
    'Privileged permission': [
        'administrator',
    ],
}

PERM_TEXT = {k: '\n'.join([f'{doc.readable_perm_name(p)}: {code(p)}' for p in v])
             for k, v in PERMISSIONS.items()}
PERM_HELP = [Embed2(description=f'{strong(k)}\n{v}')
             for k, v in PERM_TEXT.items()]
PERM_HELP = EmbedPagination(PERM_HELP, 'Permissions', False)

CHANNEL_TYPES = (TextChannel, VoiceChannel, StageChannel)

HEX_DIGITS = set(hexdigits)


def ishexdigit(s: str):
    return all(c in HEX_DIGITS for c in s)


def get_channel_map(guild: Guild) -> dict[Optional[CategoryChannel], list[GuildChannel]]:
    return {k: v for k, v in guild.by_category()}


def category_name(c: Optional[CategoryChannel]) -> str:
    if c:
        return c.name
    return '(no category)'


class ChannelFilter:
    def __init__(self, perm: Optional[Permissions2], member: Optional[Member] = None):
        if perm is None:
            self.target = ()
        elif perm <= Permissions2.text():
            self.target = TextChannel
        elif perm <= Permissions2.voice():
            self.target = (VoiceChannel, StageChannel)
        else:
            self.target = ()
        self.member = member

    def __contains__(self, channel: GuildChannel):
        p = channel.permissions_for
        return ((not self.target or isinstance(channel, self.target))
                and (not self.member or p(self.member).view_channel))


class PermFilter:
    def __init__(self, channel: Optional[GuildChannel]):
        if channel is None:
            self.target = Permissions2.all()
        elif isinstance(channel, TextChannel):
            self.target = Permissions2.all_channel() - Permissions2.voice()
        elif isinstance(channel, (VoiceChannel, StageChannel)):
            self.target = Permissions2.all_channel() - Permissions2.text()
        else:
            self.target = Permissions2.all()

    def __contains__(self, perm: Union[str, Permissions2]):
        if isinstance(perm, str):
            perm = Permissions2(**{perm: True})
        return perm <= self.target


class ServerQueryCommands:
    @command('channels')
    @doc.description('List channels in the server.')
    @doc.restriction(None, 'Will only list channels visible to you.')
    async def channels(self, ctx: Circumstances):
        await ctx.trigger_typing()
        channel_map = get_channel_map(ctx.guild)
        channels_filtered = ChannelFilter(None, ctx.author)
        fields: list[EmbedField] = []
        for category, channels in channel_map.items():
            if category not in channels_filtered:
                continue
            name = category_name(category)
            lines = [f'{code(ch.position)} {tag(ch)}'
                     for ch in channels
                     if ch in channels_filtered]
            fields.append(EmbedField(name=name, value='\n'.join(lines), inline=True))
        pages: list[Embed2] = []
        base_embed = Embed2(title='Channels').decorated(ctx.guild)
        for fieldset in chapterize_fields(fields, linebreak='newline'):
            pages.append(attr.evolve(base_embed, fields=fieldset))
        pagination = EmbedPagination(pages, 'Channels', False)
        return (await ctx.response(ctx, embed=pagination)
                .responder(pagination.with_context(ctx))
                .deleter().run())

    @command('roles')
    @doc.description('List all roles in the server, including the color codes.')
    @doc.argument('role', 'The role to check.')
    @doc.invocation((), 'List all roles.')
    @doc.invocation(('role',), 'Show info about the specified role.')
    @doc.restriction(None, (
        f"If you don't have the {strong('Manage Roles')} permission"
        ' in the server, this will only show you the roles you have'
        ' plus roles that are displayed in the sidebar separately.'
    ))
    async def roles(self, ctx: Circumstances, *, role: Optional[Role] = None):
        def getline(r):
            if r.color.value:
                return f'{tag(r)} {code(f"#{r.color.value:06x}")}'
            else:
                return tag(r)

        if role:
            roles = [role]
        else:
            roles = reversed(ctx.guild.roles)

        if not ctx.author.guild_permissions.manage_roles:
            author_roles: set[int] = {r.id for r in ctx.author.roles}
            roles = [r for r in roles if r.id in author_roles or r.hoist]

        if not roles:
            raise doc.NotAcceptable('You have no access to any of the roles you specified.')

        lines = [getline(r) for r in roles]
        body = '\n'.join(lines)
        sections = chapterize(body, 720, 720, closing='', opening='',
                              linebreak='newline')
        pages = [Embed2(description=c).decorated(ctx.guild) for c in sections]
        pagination = EmbedPagination(pages, 'Roles', False)
        return (await ctx.response(ctx, embed=pagination)
                .responder(pagination.with_context(ctx))
                .deleter().run())

    @command('perms')
    @doc.description('Survey role permissions.')
    @doc.argument('permission', ('The permission to check.'))
    @doc.argument('roles', 'The role or member whose perms to check.')
    @doc.argument('channel', (
        'Check the perms in the context of this channel.'
        ' If not supplied, check server perms.'
    ))
    @doc.invocation((), 'Show a list of permission names.')
    @doc.invocation(('channel',), False)
    @doc.invocation(('roles', 'permission'), (
        'Show if all these roles combined grant'
        ' this permission in each channel.'
    ))
    @doc.invocation(('roles', 'permission', 'channel'), (
        'Show if all these roles combined grant'
        ' this permission in this channel.'
    ))
    @doc.invocation(('roles',), (
        'Show the combined server perms of all these roles.'
    ))
    @doc.invocation(('roles', 'channel'), (
        'Show the combined perms of all'
        ' these roles in this channel.'
    ))
    @doc.invocation(('permission',), (
        'Show for each role in the server'
        ' if this permission is enabled.'
    ))
    @doc.invocation(('permission', 'channel'), (
        'Show for each role in the server'
        ' if it has this permission in this channel.'
    ))
    @doc.restriction(has_guild_permissions, manage_roles=True)
    async def perms(
        self, ctx: Circumstances,
        roles: Greedy[Union[Role, Member]],
        permission: Optional[PermissionName] = None,
        channel: Optional[Union[
            TextChannel, CategoryChannel,
            VoiceChannel, StageChannel,
        ]] = None,
    ):
        await ctx.trigger_typing()
        roles: list[Role] = [*collapse([
            r.roles if isinstance(r, Member) else r
            for r in roles
        ])]
        if not roles and not permission:
            return (
                await ctx.response(ctx, embed=PERM_HELP)
                .responder(PERM_HELP.with_context(ctx))
                .deleter().run()
            )
        channel_map = get_channel_map(ctx.guild)
        if isinstance(channel, CategoryChannel):
            channels = channel.channels
        elif channel:
            channels = [channel]
        else:
            channels = []
        if roles and permission:
            if not channels:
                channels = [*chain.from_iterable(channel_map.values())]
                channels = [c for c in channels if isinstance(c, CHANNEL_TYPES)]
            title = doc.readable_perm_name(permission.perm_name)
            title = f'Permission: {title}'
            pages = self.get_mode_at(roles, permission.get(), channels, ctx.author)
        elif roles:
            title = 'Permissions:'
            pages = self.list_mode_at(roles, channels)
        elif permission:
            title = doc.readable_perm_name(permission.perm_name)
            title = f'Permission: {title}'
            pages = self.get_perm_at(ctx.guild.roles, permission.get(), channels)

        pagination = EmbedPagination(pages, title, False)
        return (await ctx.response(ctx, embed=pagination)
                .responder(pagination.with_context(ctx))
                .deleter().run())

    def get_mode_at(
        self, roles: list[Role],
        perm: Permissions2,
        channels: list[GuildChannel],
        member: Optional[Member] = None,
    ) -> list[Embed2]:
        channel_filter = ChannelFilter(perm, member)
        channel_perms = {ch: get_total_perms(*roles, channel=ch)
                         for ch in channels if ch in channel_filter}
        result = {ch: combined.administrator or perm <= combined
                  for ch, combined in channel_perms.items()}
        categorized = map_reduce(result.items(), lambda t: t[0].category)
        content = {category_name(k): v for k, v in categorized.items()}
        description = ' '.join(tag(r) for r in roles)
        return self._perms_embeds(content, description)

    def list_mode_at(
        self, roles: list[Role],
        channels: list[GuildChannel],
    ) -> list[Embed2]:
        channel = first(channels, None)
        combined = get_total_perms(*roles, channel=channel)
        allowed = {*combined}
        categorized: defaultdict[str, list[tuple[str, bool]]] = defaultdict(list)
        perm_filter = PermFilter(channel)
        for k, ps in PERMISSIONS.items():
            for p in ps:
                if p in perm_filter:
                    categorized[k].append((doc.readable_perm_name(p), p in allowed))
        description = ' '.join(tag(r) for r in roles)
        if channel:
            description = f'{description}\nin {tag(channel)}'
        return self._perms_embeds(categorized, description)

    def get_perm_at(
        self, roles: list[Role],
        perm: Permissions2,
        channels: list[GuildChannel],
    ) -> list[Embed2]:
        channel = first(channels, None)
        role_perms = [(r, get_total_perms(r, channel=channel)) for r in roles]
        role_allowed = reversed([(tag(r), p.administrator or perm <= p)
                                 for r, p in role_perms])
        content = {'Roles': role_allowed}
        if channel:
            description = strong(f'in {tag(channel)}:')
        else:
            description = strong('Server-wide:')
        return self._perms_embeds(content, description)

    def _perms_embeds(self, content: dict[str, list[tuple[str, bool]]], description: str):
        content = {
            k: '\n'.join([
                f'{traffic_light(t)} {tag(c)}'
                for c, t in v
            ]) for k, v in content.items()
        }
        fields = [EmbedField(name=k, value=v, inline=True)
                  for k, v in content.items()]
        pages: list[Embed2] = []
        base_embed = Embed2(description=description)
        for fieldset in chapterize_fields(fields, linebreak='newline'):
            pages.append(attr.evolve(base_embed, fields=fieldset))
        return pages

    @command('snowflake', aliases=('mtime',))
    @doc.description('Get the timestamp of a Discord snowflake (ID).')
    @doc.argument('snowflake', 'The snowflake to convert.')
    async def snowflake(
        self, ctx: Circumstances, snowflake: Union[
            int, Member, Role, Message, TextChannel,
            VoiceChannel, StageChannel,
        ],
    ):
        if not isinstance(snowflake, int):
            try:
                snowflake = snowflake.id
            except AttributeError:
                raise doc.NotAcceptable('Invalid argument.')
        epoch = 1420070400000 + (snowflake >> 22)
        try:
            dt = datetime.fromtimestamp(epoch / 1000, tz=timezone.utc)
        except ValueError:
            raise doc.NotAcceptable((
                'Timestamp out of range.'
                ' Make sure the argument provided is'
                ' indeed a Discord snowflake.'
            ))
        reps = [
            code(snowflake),
            code(epoch),
            code(dt.isoformat()),
            strong(timestamp(dt, 'full')),
            timestamp(dt, 'relative'),
        ]
        res = Embed2(title='Snowflake', description='\n'.join(reps))
        return await ctx.response(ctx, embed=res).reply().run()

    @command('color')
    @doc.description('Preview a color.')
    @doc.argument('color', (
        a('CSS color accepted by PIL,',
          'https://pillow.readthedocs.io/en/stable/reference/ImageColor.html#color-names')
        + ' such as a hex code.'
    ))
    async def color(self, ctx: Circumstances, *, color: str):
        if color[0] != '#' and ishexdigit(color):
            color = f'#{color}'
        try:
            r, g, b, *a = ImageColor.getrgb(color)
        except ValueError as e:
            raise doc.NotAcceptable(str(e))
        img = Image.new('RGBA', (32, 32), (r, g, b, *a))
        data = io.BytesIO()
        img.save(data, 'png')
        data.seek(0)
        f = File(data, 'color.png')
        a = a[0] if a else 255
        h, ll, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        hexcode = f'#{rgba2int(r, g, b, a):08x}'
        h = 360 * h
        a = a / 255
        fmts = [
            strong(code(hexcode)),
            f'rgba({r}, {g}, {b}, {a:.2f})',
            f'hsla({h:.1f}deg, {s:.1%}, {ll:.1%}, {a:.1f})',
        ]
        res = Embed2(description='\n'.join(fmts), color=rgba2int(r, g, b))
        return await ctx.response(ctx, embed=res, files=[f]).reply().deleter().run()

    @command('avatar', aliases=('pfp',))
    @doc.description("Get a user's avatar (profile pic).")
    @doc.argument('member', 'The user whose avatar to get.')
    @doc.invocation((), 'Get your profile pic.')
    @doc.invocation(('member',), "Get someone else's profile pic.")
    async def avatar(self, ctx: Circumstances, member: Optional[Member]):
        if not member:
            member = ctx.author
        url = member.avatar_url_as()
        res = (Embed2(title='Avatar').personalized(member)
               .set_thumbnail(url=url)
               .set_description(code(url)))
        return await ctx.response(ctx, embed=res).deleter().run()
