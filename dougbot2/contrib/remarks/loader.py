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

from discord import Forbidden, NotFound
from discord.ext.commands import errors

from dougbot2 import exceptions
from dougbot2.blueprints import MissionControl
from dougbot2.exts.autodoc.exceptions import NoSuchCommand


def setup(bot: MissionControl):
    err = bot.errorpage

    err.add_error_fluff(
        exceptions.NotAcceptable,
        "HTTP 400 Bad Request",
        "That ain't it chief.",
        "Nope.",
        "Can't do that.",
    )
    err.add_error_fluff(
        exceptions.ServiceUnavailable,
        "HTTP 503 Service Unavailable",
    )
    err.add_error_fluff(
        errors.CommandOnCooldown,
        "HTTP 503 Service Unavailable",
        "Slow down please.",
        "Calm down satan.",
        "Not so fast.",
    )
    err.add_error_fluff(
        errors.MaxConcurrencyReached,
        "HTTP 503 Service Unavailable",
        "The line is busy.",
    )
    err.add_error_fluff(
        (
            errors.CheckFailure,
            errors.CheckAnyFailure,
            errors.MissingAnyRole,
            errors.MissingRole,
            errors.MissingPermissions,
        ),
        "HTTP 403 Forbidden",
        "You Shall Not Pass.",
        "Sorry, you can't do that in here.",
        "Nope.",
        "Nah.",
        "Not a chance.",
        "Don't even think about it.",
    )
    err.add_error_fluff(
        (errors.BotMissingAnyRole, errors.MissingRole),
        "Where my roles at?",
        "Nope, can't do that",
        "No command execution without required roles",
    )
    err.add_error_fluff(
        (errors.BotMissingPermissions, Forbidden),
        "Where my perms at?",
        "Nope, can't do that",
        "No command execution without required perms",
    )
    err.add_error_fluff(
        errors.MissingRequiredArgument,
        "Not quite there.",
        "Not quite.",
        "Almost there...",
    )
    err.add_error_fluff(errors.TooManyArguments, "Woah that's a lot.")
    err.add_error_fluff(
        (
            errors.BadArgument,
            errors.BadInviteArgument,
            errors.BadBoolArgument,
            errors.BadColourArgument,
            errors.BadUnionArgument,
            NotFound,
        ),
        "HTTP 400 Bad Request",
        "That ain't it chief.",
        "What?",
    )
    err.add_error_fluff(
        (
            errors.MessageNotFound,
            errors.MemberNotFound,
            errors.UserNotFound,
            errors.ChannelNotFound,
            errors.RoleNotFound,
            errors.EmojiNotFound,
            errors.PartialEmojiConversionFailure,
            errors.CommandNotFound,
            NoSuchCommand,
        ),
        "HTTP 404 Not Found",
        "Must be my imagination ...",
        "Must've been the wind ...",
        "What's that?",
        "You lost?",
        "Don't know what you are talking about.",
    )
    err.add_error_fluff(errors.ChannelNotReadable, "Let me in!")
    err.add_error_fluff(errors.NSFWChannelRequired, "Yikes.")
    err.add_error_fluff(
        Exception,
        "Oh no!",
        "Oopsie!",
        "Aw, snap!",
    )

    err.add_error_fluff(exceptions.DirectMessageForbidden, "Wow, rude.")
