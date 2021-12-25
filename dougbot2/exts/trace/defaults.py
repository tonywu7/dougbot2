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

import logging

from discord import Forbidden, NotFound
from discord.ext.commands import errors

from .environment import Environment, LoggingParams


def default_env() -> Environment:
    loggers: dict[str, LoggingParams] = {
        'command_throttling': {
            'name': 'Command throttling triggered',
            'level': logging.DEBUG,
        },
        'unauthorized': {
            'name': 'Bot has insufficient permissions',
            'level': logging.WARNING,
        },
        'missing_perms': {
            'name': 'Member has insufficient permissions',
            'level': logging.DEBUG,
        },
        'not_owner': {
            'name': 'Bot owner-only commands called',
            'level': logging.DEBUG,
            'stack': True,
        },
        'uncaught_exception': {
            'level': logging.ERROR,
            'title': 'Uncaught exception',
            'stack': True,
        },
    }
    exceptions: dict[str, tuple[type[Exception], ...]] = {
        'command_throttling': (
            errors.MaxConcurrencyReached,
            errors.CommandOnCooldown,
        ),
        'unauthorized': (
            errors.BotMissingAnyRole,
            errors.BotMissingPermissions,
            errors.BotMissingRole,
        ),
        'missing_perms': (
            errors.MissingPermissions,
            errors.MissingAnyRole,
            errors.MissingRole,
        ),
        'not_owner': (errors.NotOwner,),
        'uncaught_exception': (
            errors.CommandInvokeError,
            errors.ArgumentParsingError,
            errors.ConversionError,
            errors.ExtensionError,
            errors.ClientException,
        ),
    }
    ignored = {
        errors.CommandNotFound,
        errors.UserInputError,
        errors.CheckFailure,
        errors.NoPrivateMessage,
        errors.PrivateMessageOnly,
        Forbidden,
        NotFound,
    }
    env = Environment()
    env.loggers = loggers
    for cls, excs in exceptions.items():
        for exc in excs:
            env.errors[exc] = cls
    for exc in ignored:
        env.errors[exc] = False
    return env
