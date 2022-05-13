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

from discord.ext.commands import CommandError, UserInputError


class NotAcceptable(UserInputError):
    """Generic commands exception for when the input provided is malformed or unexpected.

    This is raised in command callbacks for input errors that can't be determined
    during parsing or conversion.
    """

    def __init__(self, message, *args):
        super().__init__(message=message, *args)


class ServiceUnavailable(CommandError):
    def __init__(self, message="", *args):
        super().__init__(message=message, *args)


class RollbackCommand(Exception):
    """Exception to be raised to Django transaction manager when a command finished with errors."""

    pass


class DirectMessageForbidden(CommandError):
    def __init__(self, target: str = "you"):
        super().__init__(message=f"Couldn't send DMs to {target}.")
