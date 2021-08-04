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

from inspect import ismethod

from discord.ext.commands import Command, Context, Group

from .utils.parsers.structural import (StructuralArgumentParser,
                                       StructuralParsingError)


class DelegateMixin:
    def __new__(cls, this):
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
        this = self.this
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
            return self._getattr(name)

    def __setattr__(self, name: str, value):
        return setattr(self.this, name, value)

    def __delattr__(self, name: str):
        return delattr(self.this, name)



class CommonCommandDelegate(DelegateMixin):
    async def _parse_arguments(self, ctx: Context):
        try:
            return await self._parse_structured(ctx)
        except StructuralParsingError:
            return await self._getattr('_parse_arguments')(ctx)

    async def _parse_structured(self, ctx: Context):
        await StructuralArgumentParser(ctx)()


class CommandDelegate(CommonCommandDelegate, Command):
    pass


class GroupDelegate(CommonCommandDelegate, Group):
    pass
