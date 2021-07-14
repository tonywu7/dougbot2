# strings.py
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
from collections.abc import Iterable

from discord.ext.commands import Converter
from discord.ext.commands.errors import BadArgument
from discord.utils import escape_markdown

from ...utils.markdown import code, strong
from ..autodoc.documentation import add_type_description
from ..autodoc.explanation import explains, prepend_argument_hint
from ..autodoc.lang import QuantifiedNP, coord_conj
from . import unpack_varargs


class Constant(Converter):
    def __class_getitem__(cls, const: str):
        const = unpack_varargs(const, ['const'])
        desc = QuantifiedNP(
            f'exact text "{const}"',
            concise=f'{const}',
            predicative='without the quotes',
            definite=True,
        )

        @classmethod
        async def convert(cls, ctx, arg: str):
            if arg != const:
                raise BadArgument(f'The exact string "{const}" expected.')
            return arg

        __dict__ = {'convert': convert, 'const': const}
        t = type(cls.__name__, (Converter,), __dict__)
        add_type_description(t, desc)
        return t


class Choice(Converter):
    def __class_getitem__(cls, item: tuple[Iterable[str], str, bool]):
        choices, concise_name, case_sensitive = unpack_varargs(
            item, ('choices', 'concise_name', 'case_sensitive'),
            case_sensitive=False,
        )

        if case_sensitive:
            choices = choices
        else:
            choices = {c.lower(): None for c in choices}

        fullname = concise_name + ': ' + coord_conj(*[f'"{w}"' for w in choices], conj='or')
        desc = QuantifiedNP(
            fullname, concise=concise_name,
            predicative='case sensitive' if case_sensitive else '',
        )

        @classmethod
        async def convert(cls, ctx, arg: str):
            if not case_sensitive:
                arg = arg.lower()
            if arg in choices:
                return arg
            raise InvalidChoices(desc, arg)

        __dict__ = {'convert': convert}
        t = type(cls.__name__, (Converter,), __dict__)
        add_type_description(t, desc)
        return t


class CaseInsensitive(Converter):
    async def convert(self, ctx, arg: str):
        return arg.lower()


class RegExp(Converter):
    def __class_getitem__(cls, item: tuple[str, str, str]) -> None:
        pattern, name, predicative = unpack_varargs(
            item, ('pattern', 'name', 'predicative'),
            name=None, predicative=None,
        )
        pattern: re.Pattern = re.compile(pattern)
        name = name or 'pattern'
        predicative = predicative or ('matching the regular expression '
                                      f'{code(pattern.pattern)}')
        desc = QuantifiedNP(name, predicative=predicative)

        @classmethod
        async def convert(cls, ctx, arg: str):
            matched = pattern.fullmatch(arg)
            if not matched:
                raise RegExpMismatch(desc, arg, pattern)
            return matched

        __dict__ = {'convert': convert}
        t = type(cls.__name__, (Converter,), __dict__)
        add_type_description(t, desc)
        return t


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


@explains(RegExpMismatch, 'Pattern mismatch', priority=5)
@prepend_argument_hint(True, sep='\n⚠️ ')
async def explains_regexp(ctx, exc: RegExpMismatch) -> tuple[str, int]:
    return f'Got {strong(escape_markdown(exc.received))} instead.', 30


@explains(InvalidChoices, 'Invalid choices', priority=5)
@prepend_argument_hint(True, sep='\n⚠️ ')
async def explains_invalid_choices(ctx, exc: InvalidChoices) -> tuple[str, int]:
    return f'Got {strong(escape_markdown(exc.received))} instead.', 45
