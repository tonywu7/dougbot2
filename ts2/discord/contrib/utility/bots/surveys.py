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

from collections import defaultdict
from itertools import chain
from typing import Optional, Union

import attr
from discord import (CategoryChannel, Guild, Member, Role, StageChannel,
                     TextChannel, VoiceChannel)
from discord.abc import GuildChannel
from discord.ext.commands import Greedy, command, has_guild_permissions
from more_itertools import collapse, first, map_reduce

from ts2.discord.context import Circumstances
from ts2.discord.ext import autodoc as doc
from ts2.discord.ext.types.models import PermissionName
from ts2.discord.utils.common import (Embed2, EmbedField, EmbedPagination,
                                      PermissionOverride, Permissions2,
                                      chapterize, chapterize_fields, code,
                                      get_total_perms, strong, tag,
                                      traffic_light)

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

AnyChannel = Union[TextChannel, VoiceChannel, StageChannel, CategoryChannel]
ChannelMap = dict[Optional[CategoryChannel], list[GuildChannel]]


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

    def __contains__(self, channel: Optional[GuildChannel]):
        if channel is None:
            return True
        if not self.target or isinstance(channel, self.target):
            if not self.member or channel.permissions_for(self.member).view_channel:
                return True
        return False


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


def get_channel_map(guild: Guild) -> ChannelMap:
    return {k: v for k, v in guild.by_category()}


def filter_channel_map(channel_map: ChannelMap, filter_: ChannelFilter) -> ChannelMap:
    mapped = defaultdict(list)
    for category, channels in channel_map.items():
        if category not in filter_:
            continue
        for ch in channels:
            if ch in filter_:
                mapped[category].append(ch)
    return {**mapped}


def category_name(c: Optional[CategoryChannel]) -> str:
    if c:
        return c.name
    return '(no category)'


def get_indicators(s: set[bool]) -> str:
    return ' '.join(traffic_light(v, strict=True) for v in s)


class ServerQueryCommands:
    @command('channels')
    @doc.description('List channels in the server.')
    @doc.restriction(None, 'Will only list channels visible to you.')
    async def channels(self, ctx: Circumstances):
        await ctx.trigger_typing()
        channel_map = get_channel_map(ctx.guild)
        filter_ = ChannelFilter(None, ctx.author)
        fields: list[EmbedField] = []
        for category, channels in filter_channel_map(channel_map, filter_).items():
            name = category_name(category)
            lines = [f'{code(ch.position)} {tag(ch)}'
                     for ch in channels]
            fields.append(EmbedField(name=name, value='\n'.join(lines), inline=True))
        pages: list[Embed2] = []
        base_embed = Embed2(title='Channels').decorated(ctx.guild)
        for fieldset in chapterize_fields(fields):
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
        sections = chapterize(body, 720, lambda c: c == '\n')
        pages = [Embed2(description=c).decorated(ctx.guild) for c in sections]
        pagination = EmbedPagination(pages, 'Roles', False)
        return (await ctx.response(ctx, embed=pagination)
                .responder(pagination.with_context(ctx))
                .deleter().run())

    @command('perms')
    @doc.description('Survey role permissions.')
    @doc.argument('permission', 'The permission to check.')
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
        channel: Optional[AnyChannel] = None,
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
            if roles and permission:
                channels = channel.channels
            else:
                channels = [channel]
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
            description = f'{description} in {tag(channel)}'
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
        base_embed = Embed2(description=strong(description))
        for fieldset in chapterize_fields(fields):
            pages.append(attr.evolve(base_embed, fields=fieldset))
        return pages

    @command('overrides')
    @doc.description('Survey channel overrides.')
    @doc.use_syntax_whitelist
    @doc.invocation(('target',), (
        'List all channels having any override for this role/member.'
    ))
    @doc.invocation(('permission',), (
        'List all channels having any override for this permission.'
    ))
    @doc.invocation(('target', 'permission'), (
        'List all channels having overrides for'
        ' this role/member and permission combination.'
    ))
    @doc.invocation(('channel',), (
        'List all roles/members having overrides in this channel.'
    ))
    @doc.invocation(('permission', 'channel'), (
        'List all roles/members having overrides'
        ' for this permission in this channel.'
    ))
    @doc.invocation(('target', 'channel'), (
        'List all overrides for this role/member in this channel.'
    ))
    @doc.invocation(('target', 'permission', 'channel'), (
        'Show the override for this role/member'
        ' and permission in this channel.'
    ))
    @doc.restriction(has_guild_permissions, manage_roles=True)
    async def overrides(
        self, ctx: Circumstances,
        target: Optional[Union[Role, Member]] = None,
        channel: Optional[AnyChannel] = None,
        permission: Optional[PermissionName] = None,
    ):
        if not target and not permission and not channel:
            raise doc.SendHelp()

        await ctx.trigger_typing()

        if not channel:
            channel_filter = ChannelFilter(Permissions2(view_channel=True), ctx.author)
            channel_map = get_channel_map(ctx.guild)
            channels = filter_channel_map(channel_map, channel_filter)
            pages = self.list_override_channels(channels, target, permission)

        elif not target:
            pages = self.list_override_targets(channel, permission)

        else:
            pages = self.list_overrides(channel, target, permission)

        title = 'Permission overrides'
        pagination = EmbedPagination(pages, title, False)
        return (await ctx.response(ctx, embed=pagination)
                .responder(pagination.with_context(ctx))
                .deleter().run())

    def list_override_channels(
        self, channel_map: ChannelMap,
        target: Optional[Union[Role, Member]],
        perm: Optional[PermissionName],
    ) -> list[Embed2]:

        if target is not None and perm is not None:
            def get_overrides(c: AnyChannel) -> set[Optional[bool]]:
                overwrites = c.overwrites
                if target not in overwrites:
                    return set()
                override = PermissionOverride.upgrade(c.overwrites_for(target))
                return {getattr(override, perm.perm_name)}

            description = f'{doc.readable_perm_name(perm.perm_name)}, {tag(target)}'

        elif target is not None:
            def get_overrides(c: AnyChannel) -> set[Optional[bool]]:
                overwrites = c.overwrites
                if target not in overwrites:
                    return set()
                override = PermissionOverride.upgrade(c.overwrites_for(target))
                settings = set()
                if override.allowed:
                    settings.add(True)
                if override.denied:
                    settings.add(False)
                return settings

            description = tag(target)

        elif perm is not None:
            def get_overrides(c: AnyChannel) -> set[Optional[bool]]:
                overwrites = c.overwrites
                name = perm.perm_name
                settings = set()
                for o in overwrites.values():
                    settings.add(getattr(o, name))
                return settings

            description = doc.readable_perm_name(perm.perm_name)

        else:
            raise ValueError

        results: dict[AnyChannel, set[bool]] = {}
        for c in collapse(channel_map.items()):
            if c is None:
                continue
            settings = get_overrides(c)
            settings.discard(None)
            if not settings:
                continue
            results[c] = settings

        output: dict[str, str] = {}
        for category, channels in channel_map.items():
            name = category_name(category)
            settings = results.get(category)
            if settings:
                name = f'{get_indicators(settings)} {name}'
            lines = []
            for ch in channels:
                settings = results.get(ch)
                if settings:
                    lines.append(f'{get_indicators(settings)} {tag(ch)}')
            if not lines:
                continue
            output[name] = '\n'.join(lines)

        base_embed = Embed2(description=strong(description))
        res = [EmbedField(k, v, False) for k, v in output.items()]
        pages = []
        for fieldset in chapterize_fields(res):
            pages.append(attr.evolve(base_embed, fields=fieldset))
        return pages

    def list_override_targets(
        self, channel: AnyChannel,
        perm: Optional[PermissionName],
    ) -> list[Embed2]:

        if perm:
            def get_overrides(override: PermissionOverride) -> set[Optional[bool]]:
                return {getattr(override, perm.perm_name, None)}
            description = f'{doc.readable_perm_name(perm.perm_name)} in {tag(channel)}'

        else:
            def get_overrides(override: PermissionOverride) -> set[Optional[bool]]:
                settings = set()
                if override.allowed:
                    settings.add(True)
                if override.denied:
                    settings.add(False)
                return settings
            description = f'in {tag(channel)}'

        results: dict[Union[Role, Member], set[bool]] = {}
        for target, overwrite in reversed(channel.overwrites.items()):
            override = PermissionOverride.upgrade(overwrite)
            settings = get_overrides(override)
            settings.discard(None)
            if not settings:
                continue
            results[target] = settings

        lines: list[str] = [f'{get_indicators(v)} {tag(k)}' for k, v in results.items()]
        if lines:
            content = '\n'.join(lines)
        else:
            content = '(no overrides)'
        base_embed = Embed2(description=strong(description))
        pages = []
        for chapter in chapterize(content, 720, lambda c: c == '\n'):
            pages.append(base_embed.add_field(name='Settings', value=chapter, inline=False))
        return pages

    def list_overrides(
        self, channel: AnyChannel,
        target: Union[Role, Member],
        perm: Optional[PermissionName],
    ):
        description = f'{tag(target)} in {tag(channel)}'
        settings: dict[str, bool] = {}
        override = PermissionOverride.upgrade(channel.overwrites_for(target))
        for p in override.allowed:
            settings[p] = True
        for p in override.denied:
            settings[p] = False
        if perm:
            name = perm.perm_name
            settings = {name: settings.get(name)}

        lines = [f'{traffic_light(v, True)} {doc.readable_perm_name(k)}'
                 for k, v in settings.items()]
        if lines:
            content = '\n'.join(lines)
        else:
            content = '(no overrides)'
        base_embed = Embed2(description=strong(description))
        pages = []
        for chapter in chapterize(content, 720, lambda c: c == '\n'):
            pages.append(base_embed.add_field(name='Settings', value=chapter, inline=False))
        return pages
