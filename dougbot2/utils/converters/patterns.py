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

from .utils import unpack_varargs


class Constant(Converter):
    """Converter accepting an exact string.

    Useful for arguments that act as flags. Usage:

        async def command(ctx, delete: Constant[Literal['delete']])
        # accept the exact text "delete"
    """

    const: str

    def __class_getitem__(cls, const: str):
        const = unpack_varargs(const, ["const"])[0]

        @classmethod
        async def convert(cls, ctx, arg: str | bool):
            if arg is True:
                return const
            if arg != const:
                raise BadArgument(f'The exact string "{const}" expected.')
            return arg

        __dict__ = {"convert": convert, "const": const}
        t = type(cls.__name__, (cls,), __dict__)
        return t


class Choice(Converter):
    """Converter accepting one of several exact strings.

    By default it is case-insensitive.

    Usage:

        async def command(ctx, types: Choice[Literal['member', 'role']])
    """

    choices: Iterable[str]
    name: str
    case_sensitive: bool

    def __class_getitem__(cls, item: tuple[Iterable[str], str, bool]):
        choices, name, case_sensitive = unpack_varargs(
            item,
            ("choices", "name", "case_sensitive"),
            case_sensitive=False,
            name=None,
        )
        if name is None:
            name = "/".join(choices)
        if isinstance(name, tuple):
            name = name[0]

        if case_sensitive:
            choices = {c: c for c in choices}
        else:
            choices = {c.lower(): c for c in choices}

        @classmethod
        async def convert(cls, ctx, arg: str):
            if not case_sensitive:
                to_match = arg.lower()
            else:
                to_match = arg
            matched = choices.get(to_match)
            if matched is not None:
                return matched
            raise InvalidChoices(t, arg)

        __dict__ = {
            "convert": convert,
            "choices": choices,
            "name": name,
            "case_sensitive": case_sensitive,
        }
        t = type(cls.__name__, (cls,), __dict__)
        return t


class Lowercase(Converter):
    """Convert the argument to lowercase."""

    async def convert(self, ctx, arg: str):
        return arg.lower()


class BoundedNumber(Converter):
    """Accept a number only if it is within the specified bounds (both inclusive).

    Usage:

        async def command(ctx, number: BoundedNumber[Literal[24, 72]])
        # accept a number >= 24 and <= 72
    """

    lower: float
    upper: float

    def __class_getitem__(cls, item: tuple[int, int]):
        lower, upper = unpack_varargs(item, ("bounds",))

        @classmethod
        async def convert(cls, ctx, arg: str):
            try:
                num = float(arg)
            except ValueError:
                raise NumberOutOfBound(t, arg)
            if not lower <= num <= upper:
                raise NumberOutOfBound(t, arg)
            return num

        __dict__ = {"convert": convert, "lower": lower, "upper": upper}
        t = type(cls.__name__, (cls,), __dict__)
        return t


class RegExp(Converter):
    r"""Converter accepting any string matching the provided regular expression.

    Usage:

        async def command(ctx, a_number: RegExp[Literal[r'[Aa]\d+']]
    """

    pattern: re.Pattern
    name: str
    description: str

    def __class_getitem__(cls, item: tuple[str, str, str]) -> None:
        pattern, name, description = unpack_varargs(item, ("args",))
        pattern: re.Pattern = re.compile(pattern)
        name = name or "pattern"

        @classmethod
        async def convert(cls, ctx, arg: str):
            matched = pattern.fullmatch(arg)
            if not matched:
                raise RegExpMismatch(t, arg)
            return matched

        __dict__ = {
            "convert": convert,
            "pattern": pattern,
            "name": name,
            "description": description,
        }
        t = type(cls.__name__, (cls,), __dict__)
        return t


class InvalidChoices(BadArgument):
    """Raised when the argument is not any of the items accepted by a Choice converter."""

    def __init__(self, choices: Choice, found: str, *args):
        self.choices = choices
        self.received = found
        message = f'Invalid choice "{found}". Choices are one of: {", ".join(choices.choices)}'
        super().__init__(message=message, *args)


class NumberOutOfBound(BadArgument):
    """Raised when the argument represents a number but is out of bound for a BoundedNumber converter."""

    def __init__(self, num_range: BoundedNumber, found: str, *args):
        self.received = found
        message = (
            f'Invalid value "{found}". Must be a number'
            f" between {num_range.lower} and {num_range.upper} (inclusive)."
        )
        super().__init__(message=message, *args)


class RegExpMismatch(BadArgument):
    """Raise when the argument does not match the required regular expression for a RegExp converter."""

    def __init__(self, expected: RegExp, arg: str):
        self.expected = expected
        self.received = arg
        message = f"Argument should be {expected.name}: {expected.description}"
        super().__init__(message=message)
