# defaults.py
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

from functools import partial
from typing import Union

import discord
from discord.ext import commands
from more_itertools import partition

from ...utils.english import (QuantifiedNP, pl_cat_attributive,
                              readable_perm_name)
from ...utils.markdown import strong
from .environment import Environment, TypeDictionary

_AnyChannel = Union[discord.TextChannel, discord.VoiceChannel,
                    discord.StageChannel, discord.CategoryChannel]
_TextAndVCs = Union[discord.TextChannel, discord.VoiceChannel]


def _record_perm_check(env, deco, place: str, **perms: bool) -> str:
    denied, allowed = partition(lambda t: t[1], perms.items())
    denied = [strong(readable_perm_name(s)) for s, v in denied]
    allowed = [strong(readable_perm_name(s)) for s, v in allowed]
    msg = []
    if allowed:
        msg.append(f'Requires {pl_cat_attributive("perm", allowed)} in {place}')
    if denied:
        msg.append(f'Denies anyone with {pl_cat_attributive("perm", denied)} in {place}')
    return '\n'.join(msg)


def _record_owner_check(env, deco) -> str:
    return "Only the bot's owner can use this command."


_record_server_perm_check = partial(_record_perm_check, 'server')
_record_channel_perm_check = partial(_record_perm_check, 'channel')


def default_env() -> Environment:
    """Create a default Environment for autodoc generation."""
    types = TypeDictionary()

    defaults = {
        int: QuantifiedNP('number'),
        float: QuantifiedNP('number', attributive='whole or decimal'),

        str: QuantifiedNP('text', uncountable=True),
        bool: QuantifiedNP('yes or no', concise='yes/no', definite=True, uncountable=True),

        discord.Member: QuantifiedNP('id', 'name', 'mention', concise='user', attributive="Discord user's"),
        discord.Message: QuantifiedNP('id', 'URL', concise='message', attributive="message's"),
        discord.PartialMessage: QuantifiedNP('id', 'URL', concise='message', attributive="message's"),
        discord.Role: QuantifiedNP('id', 'name', 'mention', concise='role', attributive="role's"),
        discord.TextChannel: QuantifiedNP('id', 'name', concise='text channel', attributive="text channel's"),
        discord.VoiceChannel: QuantifiedNP('id', 'name', concise='voice channel', attributive="voice channel's"),
        discord.StageChannel: QuantifiedNP('id', 'name', concise='stage channel', attributive="stage channel's"),
        discord.CategoryChannel: QuantifiedNP('id', 'name', concise='channel category',
                                              attributive="channel category's"),
        discord.Colour: QuantifiedNP('color', predicative='in hexadecimal or RGB format'),
        discord.Emoji: QuantifiedNP('emote', predicative='must be in servers the bot is in'),
        discord.PartialEmoji: QuantifiedNP('emote id'),
        discord.Guild: QuantifiedNP('id', 'name', concise='server', attributive="server's"),

        _AnyChannel: QuantifiedNP('id', 'name', concise='channel', attributive="channel's"),
        _TextAndVCs: QuantifiedNP('id', 'name', concise='channel', attributive="channel's"),

        commands.has_permissions: _record_channel_perm_check,
        commands.has_guild_permissions: _record_server_perm_check,
        commands.is_owner: _record_owner_check,
    }

    types._dict.update(defaults)
    env = Environment(types)
    return env
