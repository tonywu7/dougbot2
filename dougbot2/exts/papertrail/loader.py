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

from ...blueprints import MissionControl


def setup(bot: MissionControl):
    console = bot.console
    console.register_logger(
        'command_throttling',
        errors.MaxConcurrencyReached,
        errors.CommandOnCooldown,
        title='Command throttling triggered',
        level=logging.DEBUG,
    )
    console.register_logger(
        'bot_forbidden',
        errors.BotMissingAnyRole,
        errors.BotMissingPermissions,
        errors.BotMissingRole,
        title='Bot has insufficient permissions',
        level=logging.WARNING,
    )
    console.register_logger(
        'member_forbidden',
        errors.MissingPermissions,
        errors.MissingAnyRole,
        errors.MissingRole,
        title='Member has insufficient permissions',
        level=logging.DEBUG,
    )
    console.register_logger(
        'not_owner',
        errors.NotOwner,
        title='Owner-only commands called',
        level=logging.DEBUG,
    )
    console.register_logger(
        'uncaught_exception',
        errors.CommandInvokeError,
        errors.ArgumentParsingError,
        errors.ConversionError,
        errors.ExtensionError,
        errors.ClientException,
        title='Uncaught exception',
        level=logging.ERROR,
        show_stacktrace=True,
    )

    console.ignore_exception(
        errors.CommandNotFound,
        errors.UserInputError,
        errors.CheckFailure,
        errors.NoPrivateMessage,
        errors.PrivateMessageOnly,
        Forbidden,
        NotFound,
    )
