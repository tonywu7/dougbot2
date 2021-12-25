# exceptions.py
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
from typing import Union

from discord import Forbidden, NotFound
from discord.ext.commands import CommandError, UserInputError, errors

from . import cog


class NotAcceptable(UserInputError):
    """Generic commands exception for when the input provided is malformed or unexpected.

    This is raised in command callbacks for input errors that can't be determined
    during parsing or conversion.
    """
    def __init__(self, message, *args):
        super().__init__(message=message, *args)


class ServiceUnavailable(CommandError):
    def __init__(self, message='', *args):
        super().__init__(message=message, *args)


EXTRA_ALERTS: dict[
    Union[type[Exception], tuple[type[Exception], ...]],
    tuple[str, ...],
] = {
    NotAcceptable: (
        'HTTP 400 Bad Request',
        "That ain't it chief.",
        'Nope.',
        "Can't do that.",
    ),
    ServiceUnavailable: (
        'Temporarily unavailable',
        'HTTP 503 Service Unavailable',
    ),
    errors.CommandOnCooldown: (
        'HTTP 503 Service Unavailable',
        'Slow down please.',
        'Calm down satan.',
        'Not so fast.',
    ),
    errors.MaxConcurrencyReached: (
        'HTTP 503 Service Unavailable',
        'The line is busy.',
    ),
    (errors.CheckFailure,
     errors.CheckAnyFailure,
     errors.MissingAnyRole,
     errors.MissingRole,
     errors.MissingPermissions,
     cog.ModuleDisabled): (
        'HTTP 403 Forbidden',
        'You Shall Not Pass.',
        "Sorry, you can't do that in here.",
        'Nope.',
        'Nah.',
        'Not a chance.',
        "Don't even think about it.",
    ),
    (errors.BotMissingAnyRole,
     errors.MissingRole): (
        'Where my roles at?',
        "Nope, can't do that",
        'No command execution without required roles',
    ),
    (errors.BotMissingPermissions,
     Forbidden): (
        'Where my perms at?',
        "Nope, can't do that",
        'No command execution without required perms',
    ),
    errors.MissingRequiredArgument: (
        'Not quite there.',
        'Not quite.',
        'Almost there...',
    ),
    errors.TooManyArguments: (
        'This is a lot.',
    ),
    (errors.BadArgument,
     errors.BadInviteArgument,
     errors.BadBoolArgument,
     errors.BadColourArgument,
     errors.BadUnionArgument,
     NotFound): (
        'HTTP 400 Bad Request',
        "That ain't it chief.",
        'What?',
    ),
    (errors.MessageNotFound,
     errors.MemberNotFound,
     errors.UserNotFound,
     errors.ChannelNotFound,
     errors.RoleNotFound,
     errors.EmojiNotFound,
     errors.PartialEmojiConversionFailure,
     errors.CommandNotFound): (
        'HTTP 404 Not Found',
        'Must be my imagination ...',
        "Must've been the wind ...",
        "What's that?",
        'You lost?',
        "Don't know what you are talking about.",
    ),
    errors.ChannelNotReadable: (
        'Let me in!',
    ),
    errors.NSFWChannelRequired: (
        'Yikes.',
    ),
    Exception: (
        'Oh no!',
        'Oopsie!',
        'Aw, snap!',
    ),
}


async def _on_service_unavailable(ctx, exc: ServiceUnavailable):
    return f'{exc}\nPlease try again later.'


def setup_alerts(bot):
    config = defaultdict(dict, {
        NotAcceptable: {'handler': lambda ctx, exc: str(exc)},
        ServiceUnavailable: {'handler': _on_service_unavailable},
        cog.ModuleDisabled: {'handler': lambda ctx, exc: str(exc), 'alerts': 'Module disabled'}
    })
    for excs, alerts in EXTRA_ALERTS.items():
        if not isinstance(excs, tuple):
            excs = (excs,)
        for exc_t in excs:
            config[exc_t].update({'alerts': alerts})
    return config
