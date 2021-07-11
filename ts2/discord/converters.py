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
from collections import defaultdict
from collections.abc import Callable, Iterable
from functools import wraps
from inspect import Parameter, signature
from operator import itemgetter
from typing import (Any, Generic, Literal, Optional, Protocol, TypeVar, Union,
                    get_args, get_origin, overload)

import pytz
from discord import Member, Permissions, Role
from discord.abc import GuildChannel
from discord.ext.commands import Converter
from discord.ext.commands.errors import (BadArgument, CommandError,
                                         MissingRequiredArgument)
from discord.utils import escape_markdown

from ts2.utils.lang import QuantifiedNP, coord_conj

from .context import Circumstances
from .errors import explains, prepend_argument_hint
from .utils.markdown import a, code, strong
from .utils.models import HypotheticalRole

T = TypeVar('T')
U = TypeVar('U')


def _unpack_varargs(item: tuple, names: list[str], **defaults):
    if not isinstance(item, tuple):
        item = (item,)
    unpacked = {**defaults, **dict(zip(names, item))}
    for k in unpacked:
        v = unpacked[k]
        if get_origin(v) is Literal:
            unpacked[k] = get_args(v)[0]
    return itemgetter(*names)(unpacked)


class DoesConversion(Protocol[T]):
    @classmethod
    async def convert(ctx: Circumstances, arg: str) -> T:
        ...


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
        const = _unpack_varargs(const, ['const'])
        __accept__ = QuantifiedNP(
            f'exact text "{const}"',
            concise=f'{const}',
            predicative='without the quotes',
            definite=True,
        )

        @classmethod
        async def convert(cls, ctx: Circumstances, arg: str):
            if arg != const:
                raise BadArgument(f'The exact string "{const}" expected.')
            return arg

        __dict__ = {'__accept__': __accept__, 'convert': convert}
        return type(cls.__name__, (Converter,), __dict__)


class Choice(Converter):
    def __class_getitem__(cls, item: tuple[Iterable[str], str, bool]):
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
        return type(cls.__name__, (Converter,), __dict__)


class CaseInsensitive(Converter):
    __accept__ = QuantifiedNP('text', predicative='case insensitive')

    async def convert(self, ctx: Circumstances, arg: str):
        return arg.lower()


class RegExp(Converter):
    def __class_getitem__(cls, item: tuple[str, str, str]) -> None:
        pattern, name, predicative = _unpack_varargs(
            item, ('pattern', 'name', 'predicative'),
            name=None, predicative=None,
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


class Timezone(Converter, pytz.BaseTzInfo):
    __accept__ = QuantifiedNP(
        'IANA tz code', predicative=(
            f'see {a("https://en.wikipedia.org/wiki/List_of_tz_database_time_zones", "list of timezones")}'
        ))

    def __init__(self) -> None:
        pass

    async def convert(self, ctx: Circumstances, argument: str) -> pytz.BaseTzInfo:
        try:
            return pytz.timezone(argument)
        except pytz.UnknownTimeZoneError:
            raise BadArgument(f'Unknown timezone {code(escape_markdown(argument))}')


class Fallback:
    def __class_getitem__(cls, item):
        return Union[item, Literal[False], str, None]


class RetainsError(Generic[T, U]):
    name = '<param>'

    def __init__(self, result: T = Parameter.empty,
                 default: U = Parameter.empty,
                 argument: Optional[str] = None,
                 error: Optional[Exception] = None):
        self.result = result
        self.default = default
        self.argument = argument
        self.error = error

    @property
    def value(self):
        if self.result is not Parameter.empty:
            return self.result
        elif self.default is not Parameter.empty:
            return self.default
        raise ValueError

    @classmethod
    def ensure(cls, f):
        sig = signature(f)
        paramlist = [*sig.parameters.values()]
        defaults = {}
        defaultslist = []
        for k, v in sig.parameters.items():
            if isinstance(v.annotation, str):
                annotation = eval(v.annotation, f.__globals__)
            else:
                annotation = v.annotation
            try:
                converter: cls = get_args(annotation)[0]
                defaults[k] = converter.default
            except (AttributeError, IndexError):
                defaults[k] = v.default
        defaultslist = [*defaults.values()]

        @wraps(f)
        async def wrapped(*args, **kwargs):
            args_ = []
            for i, arg in enumerate(args):
                if arg is None:
                    default_ = defaultslist[i]
                    if default_ is Parameter.empty:
                        raise MissingRequiredArgument(paramlist[i])
                    args_.append(cls(default=default_))
                else:
                    args_.append(arg)
            kwargs_ = {}
            for k, v in kwargs.items():
                if v is None:
                    default_ = defaults[k]
                    if default_ is Parameter.empty:
                        raise MissingRequiredArgument(sig.parameters[k])
                    kwargs_[k] = cls(default=default_)
                else:
                    kwargs_[k] = v
            return await f(*args_, **kwargs_)
        return wrapped

    def __class_getitem__(cls, item: tuple[DoesConversion[T], Any]):
        converter, default = _unpack_varargs(item, ('converter', 'default'), default=None)

        @classmethod
        async def convert(_, ctx: Circumstances, arg: str):
            try:
                result = await ctx.command._actual_conversion(ctx, converter, arg, cls)
                return cls(result)
            except CommandError as e:
                ctx.view.undo()
                return cls(default=default, argument=arg, error=e)

        __dict__ = {'convert': convert, 'default': default, '_converter': converter}
        return Union[type(cls.__name__, (RetainsError, Converter), __dict__), None]

    @classmethod
    def asdict(cls, **items: RetainsError) -> dict:
        return defaultdict(lambda: None, {k: v.value for k, v in items.items() if v.value is not None})

    @classmethod
    def astuple(cls, *items: RetainsError) -> tuple:
        return tuple(v.value for v in items)

    @classmethod
    def errordict(cls, **items: RetainsError) -> dict:
        errors = {}
        for k, v in items.items():
            if v.error is not None:
                errors[k] = v.error
        return errors

    @classmethod
    def unpack(cls, **items: RetainsError) -> tuple[dict, dict]:
        return cls.asdict(**items), cls.errordict(**items)


class ReplyRequired(BadArgument):
    def __call__(self):
        return super().__call__(message='You need to call this command while replying to a message.')


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


class InvalidSyntax(BadArgument):
    def __init__(self, message, *args):
        super().__init__(message=message, *args)


@explains(RegExpMismatch, 'Pattern mismatch', priority=5)
@prepend_argument_hint(True, sep='\n⚠️ ')
async def explains_regexp(ctx: Circumstances, exc: RegExpMismatch) -> tuple[str, int]:
    return f'Got {strong(escape_markdown(exc.received))} instead.', 30


@explains(InvalidChoices, 'Invalid choices', priority=5)
@prepend_argument_hint(True, sep='\n⚠️ ')
async def explains_invalid_choices(ctx: Circumstances, exc: InvalidChoices) -> tuple[str, int]:
    return f'Got {strong(escape_markdown(exc.received))} instead.', 45


@explains(InvalidSyntax, 'Usage Error', priority=5)
async def explains_usage_error(ctx: Circumstances, exc) -> tuple[str, int]:
    return str(exc), 30


@explains(ReplyRequired, 'Message reference required', priority=5)
async def explains_required_reply(ctx: Circumstances, exc) -> tuple[str, int]:
    return str(exc), 20
