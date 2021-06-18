# converters.py
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

from __future__ import annotations

from typing import Callable, Optional, TypeVar, overload

from discord import Member, Permissions, Role
from discord.abc import GuildChannel
from discord.ext.commands import Converter
from discord.ext.commands.errors import BadArgument

from telescope2.utils.lang import QuantifiedNP, coord_conj

from .context import Circumstances
from .utils.models import HypotheticalRole


class PermissionName(Converter):
    accept = QuantifiedNP('permission name', predicative='see [this page](https://discordpy.readthedocs.io/en/'
                          'stable/api.html#discord.Permissions) for a list')

    perm_name: str

    async def convert(self, ctx: Circumstances, arg: str) -> Callable[[Role], bool]:
        if not hasattr(Permissions, arg):
            raise BadArgument(
                f'No such permission {arg}\n'
                'Consult https://discordpy.readthedocs.io/'
                'en/stable/api.html#discord.Permissions '
                'for a list of possible attributed.',
            )
        self.perm_name = arg
        return self

    def __str__(self):
        return self.perm_name

    @overload
    def __call__(self, entity: Role, channel: None) -> bool:
        ...

    @overload
    def __call__(self, entity: Member, channel: None) -> bool:
        ...

    @overload
    def __call__(self, entity: Member, channel: GuildChannel) -> bool:
        ...

    def __call__(self, entity: Role | Member, channel: Optional[GuildChannel] = None) -> bool:
        if channel:
            return getattr(channel.permissions_for(entity), self.perm_name)
        if isinstance(entity, Member):
            entity = HypotheticalRole(*entity.roles)
        return entity.permissions.administrator or getattr(entity.permissions, self.perm_name)


class Constant(Converter):
    def __init__(self, value: str = '::') -> None:
        self.const = value

    @property
    def accept(self):
        return QuantifiedNP(f'the exact text "{self.const}"', concise=f'"{self.const}"', predicative='without the quotes')

    async def convert(self, ctx: Circumstances, arg: str):
        if arg != self.const:
            raise BadArgument(f'Constant value {self.const} expected')


class Choice(Converter, TypeVar, _root=True):
    def __init__(self, *choices: str, concise_name: str, case_sensitive: bool = False) -> None:
        self.case_sensitive = case_sensitive
        if case_sensitive:
            self.choices = choices
        else:
            self.choices = {c.lower() for c in choices}
        self.concise = concise_name

    @property
    def accept(self):
        fullname = self.concise + ': ' + coord_conj(*[f'"{w}"' for w in self.choices], conj='or')
        return QuantifiedNP(fullname, concise=self.concise, predicative='case sensitive' if self.case_sensitive else '')

    async def convert(self, ctx: Circumstances, arg: str):
        if not self.case_sensitive:
            arg = arg.lower()
        if arg in self.choices:
            return arg
        raise BadArgument(f'Invalid choice {arg}. Choices are {self.accept.one_of()}')


class CaseInsensitive(Converter, TypeVar, _root=True):
    accept = QuantifiedNP('text', predicative='case insensitive')

    def __init__(self) -> None:
        return

    async def convert(self, ctx: Circumstances, arg: str):
        return arg.lower()
