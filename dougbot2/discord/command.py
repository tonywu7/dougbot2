# command.py
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
from inspect import ismethod

from discord.ext.commands import Command, Context, Group, command, group

from ..utils.parsers.structural import (
    StructuralArgumentParser, StructuralParsingError,
)


class DelegateMixin:
    """Mixin that intercepts all attribute access and delegate it to an underlying object."""

    def __new__(cls, this):  # noqa: D102
        obj = object.__new__(cls)
        obj.__dict__['this'] = this
        return obj

    def __init__(self, *args, **attrs):
        return

    def _getattr(self, name: str):
        this = object.__getattribute__(self, 'this')
        item = getattr(this, name)
        if not ismethod(item):
            return item
        that = item.__self__
        if that is not this:
            return item
        unbound = getattr(type(that), name)
        return unbound.__get__(self)

    def unwrap(self):
        """Access the underlying object."""
        this = object.__getattribute__(self, 'this')
        while True:
            if isinstance(this, DelegateMixin):
                this = this.unwrap()
            else:
                break
        return this

    def __getattribute__(self, name: str):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return object.__getattribute__(self, '_getattr')(name)

    def __setattr__(self, name: str, value):
        return setattr(object.__getattribute__(self, 'this'), name, value)

    def __delattr__(self, name: str):
        return delattr(object.__getattribute__(self, 'this'), name)


class CommonCommandDelegate(DelegateMixin):
    """Mixin for `discord.ext.commands.Command`.

    Override _parse_arguments to implement structural argument parsing
    (using JSON/TOML code blocks as command input).
    """

    async def _parse_arguments(self, ctx: Context):
        try:
            return await self._parse_structured(ctx)
        except StructuralParsingError:
            return await self._getattr('_parse_arguments')(ctx)

    async def _parse_structured(self, ctx: Context):
        await StructuralArgumentParser(ctx)()


class CommandDelegate(CommonCommandDelegate, Command):
    """Subclass for `discord.ext.commands.Command` with mixins.

    Substitute the original class in command creation.
    """
    pass


class GroupDelegate(CommonCommandDelegate, Group):
    """Subclass for `discord.ext.commands.Group` with mixins.

    Substitute the original class in command group creation.
    """
    pass


command = command
topic = partial(group, case_insensitive=True, invoke_without_command=True)
