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

import re
from operator import itemgetter
from typing import Callable, Iterable, List, Literal, Optional, Tuple, overload

from discord import Member, Permissions, Role
from discord.abc import GuildChannel
from discord.ext.commands import Converter
from discord.ext.commands.errors import BadArgument

from telescope2.utils.lang import QuantifiedNP, coord_conj

from .context import Circumstances
from .utils.markdown import code
from .utils.models import HypotheticalRole


def _unpack_varargs(item: Tuple, names: List[str], **defaults):
    if not isinstance(item, tuple):
        item = (item,)
    unpacked = {**defaults, **dict(zip(names, item))}
    for k in unpacked:
        v = unpacked[k]
        try:
            if v.__origin__ is Literal:
                unpacked[k] = v.__args__[0]
        except AttributeError:
            pass
    return itemgetter(*names)(unpacked)


class PermissionName(Converter):
    __accept__ = QuantifiedNP('permission name', predicative='see [this page](https://discordpy.readthedocs.io/en/'
                              'stable/api.html#discord.Permissions) for a list')

    perm_name: str

    async def convert(self, ctx: Circumstances, arg: str) -> Callable[[Role], bool]:
        if not hasattr(Permissions, arg):
            if not hasattr(Permissions, arg.replace('server', 'guild')):
                raise BadArgument(f'No such permission {arg}')
            else:
                arg = arg.replace('server', 'guild')
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
    def __class_getitem__(cls, const: str):
        const = _unpack_varargs(const)
        __accept__ = QuantifiedNP(f'the exact text "{const}"',
                                  concise=f'"{const}"',
                                  predicative='without the quotes')

        @classmethod
        async def convert(ctx: Circumstances, arg: str):
            if arg != const:
                raise BadArgument(f'The exact string "{const}" expected.')
            return arg

        __dict__ = {'__accept__': __accept__, 'convert': convert}
        return type(cls.__name__, (Converter, str,), __dict__)


class Choice(Converter):
    def __class_getitem__(cls, item: Tuple[Iterable[str], str, bool]):
        choices, concise_name, case_sensitive = _unpack_varargs(
            item, ('choices', 'concise_name', 'case_sensitive'),
            case_sensitive=False,
        )

        if case_sensitive:
            choices = choices
        else:
            choices = {c.lower(): None for c in choices}

        fullname = concise_name + ': ' + coord_conj(*[f'"{w}"' for w in choices], conj='or')
        __accept__ = QuantifiedNP(fullname, concise=concise_name,
                                  predicative='case sensitive' if case_sensitive else '')

        @classmethod
        async def convert(cls, ctx: Circumstances, arg: str):
            if not case_sensitive:
                arg = arg.lower()
            if arg in choices:
                return arg
            raise InvalidChoices(__accept__, arg)

        __dict__ = {'__accept__': __accept__, 'convert': convert}
        return type(cls.__name__, (Converter, str,), __dict__)


class CaseInsensitive(Converter):
    __accept__ = QuantifiedNP('text', predicative='case insensitive')

    async def convert(self, ctx: Circumstances, arg: str):
        return arg.lower()


class RegExp(Converter):
    def __class_getitem__(cls, item: Tuple[str, str, str]) -> None:
        pattern, name, predicative = _unpack_varargs(
            item, ('pattern', 'name', 'predicative'),
            concise=None, predicative=None,
        )
        pattern: re.Pattern = re.compile(pattern)
        name = name or 'pattern'
        predicative = predicative or ('matching the regular expression '
                                      f'{code(pattern.pattern)}')
        __accept__ = QuantifiedNP(name, predicative=predicative)

        @classmethod
        async def convert(cls, ctx: Circumstances, arg: str):
            matched = pattern.fullmatch(arg)
            if not matched:
                raise RegExpMismatch(__accept__, arg, pattern)
            return matched

        __dict__ = {'__accept__': __accept__, 'convert': convert}
        return type(cls.__name__, (Converter,), __dict__)


class InvalidChoices(BadArgument):
    def __init__(self, choices: QuantifiedNP, found: str, *args):
        self.choices = choices
        self.received = found
        message = f'Invalid choice "{found}". Choices are {choices.one_of()}'
        super().__init__(message=message, *args)


class RegExpMismatch(BadArgument):
    def __init__(self, expected: QuantifiedNP, arg: str, pattern: re.Pattern, *args):
        self.expected = expected
        self.received = arg
        self.pattern = pattern
        message = f'Argument should be {self.expected.a()}'
        super().__init__(message=message, *args)
