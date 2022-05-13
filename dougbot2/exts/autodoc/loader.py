# loader.py
# Copyright (C) 2022  @tonyzbf +https://github.com/tonyzbf/
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

from ...blueprints import MissionControl
from ...utils.english import QuantifiedNP as NP, pl_cat_attributive, readable_perm_name
from ...utils.markdown import strong
from .exceptions import NoSuchCommand

_AnyChannel = Union[
    discord.TextChannel,
    discord.VoiceChannel,
    discord.StageChannel,
    discord.CategoryChannel,
]
_TextAndVCs = Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel]
_VCs = Union[discord.VoiceChannel, discord.StageChannel]


def _record_perm_check(deco, place: str, **perms: bool) -> str:
    denied, allowed = partition(lambda t: t[1], perms.items())
    denied = [strong(readable_perm_name(s)) for s, v in denied]
    allowed = [strong(readable_perm_name(s)) for s, v in allowed]
    msg = []
    if allowed:
        msg.append(f'Requires {pl_cat_attributive("perm", allowed)} in {place}')
    if denied:
        msg.append(
            f'Denies anyone with {pl_cat_attributive("perm", denied)} in {place}'
        )
    return "\n".join(msg)


def _record_owner_check(deco) -> str:
    return "Only the bot's owner can use this command."


_record_server_perm_check = partial(_record_perm_check, place="server")
_record_channel_perm_check = partial(_record_perm_check, place="channel")


def setup(bot: MissionControl) -> None:
    doc = bot.manpage

    doc.register_type(int, NP("number"))
    doc.register_type(float, NP("number", attributive="whole or decimal"))

    doc.register_type(str, NP("text", uncountable=True))
    doc.register_type(
        bool, NP("yes or no", concise="yes/no", definite=True, uncountable=True)
    )

    doc.register_type(
        discord.User,
        NP("ID", "name", "mention", concise="user", attributive="Discord user's"),
    )
    doc.register_type(
        discord.Member,
        NP("ID", "name", "mention", concise="user", attributive="Discord user's"),
    )
    doc.register_type(
        discord.Message, NP("ID", "URL", concise="message", attributive="message's")
    )
    doc.register_type(
        discord.PartialMessage,
        NP("ID", "URL", concise="message", attributive="message's"),
    )
    doc.register_type(
        discord.Role, NP("ID", "name", "mention", concise="role", attributive="role's")
    )
    doc.register_type(
        discord.TextChannel,
        NP("ID", "name", concise="text channel", attributive="text channel's"),
    )
    doc.register_type(
        discord.VoiceChannel,
        NP("ID", "name", concise="voice channel", attributive="voice channel's"),
    )
    doc.register_type(
        discord.StageChannel,
        NP("ID", "name", concise="stage channel", attributive="stage channel's"),
    )
    doc.register_type(
        discord.CategoryChannel,
        NP("ID", "name", concise="channel category", attributive="channel category's"),
    )
    doc.register_type(
        discord.Colour, NP("color", predicative="in hexadecimal or RGB format")
    )
    doc.register_type(
        discord.Emoji, NP("emote", predicative="must be in servers the bot is in")
    )
    doc.register_type(discord.PartialEmoji, NP("emote ID"))
    doc.register_type(
        discord.Guild, NP("ID", "name", concise="server", attributive="server's")
    )

    doc.register_type(
        _AnyChannel, NP("ID", "name", concise="channel", attributive="channel's")
    )
    doc.register_type(
        _TextAndVCs, NP("ID", "name", concise="channel", attributive="channel's")
    )
    doc.register_type(
        _VCs, NP("ID", "name", concise="channel", attributive="voice channel's")
    )

    doc.register_type(commands.has_permissions, _record_channel_perm_check)
    doc.register_type(commands.has_guild_permissions, _record_server_perm_check)
    doc.register_type(commands.is_owner, _record_owner_check)

    def deferred() -> None:
        doc.load_commands(bot)
        doc.finalize()
        bot.errorpage.set_error_blurb(NoSuchCommand, bot.errorpage.exception_to_str)
        bot.errorpage.add_error_fluff(NoSuchCommand, "Command not found")
        bot.console.ignore_exception(NoSuchCommand)

    bot.defer_init(deferred)
