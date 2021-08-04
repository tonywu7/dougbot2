# functional.py
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

from collections import defaultdict
from functools import wraps
from inspect import Parameter, signature
from typing import Any, Generic, Optional, Protocol, TypeVar, Union, get_args

from discord.ext.commands import Context, Converter
from discord.ext.commands.errors import CommandError, MissingRequiredArgument

from ..autodoc.decorators import convert_with
from . import unpack_varargs

T = TypeVar('T')
U = TypeVar('U')
R = TypeVar('R')


class DoesConversion(Protocol[T]):
    @classmethod
    async def convert(ctx: Context, arg: str) -> T:
        ...


@convert_with(lambda t: t._converter)
class Maybe(Converter, Generic[T, U]):
    name = '<param>'

    def __init__(self, position: int = 0,
                 result: T = Parameter.empty,
                 default: U = Parameter.empty,
                 argument: Optional[str] = None,
                 error: Optional[Exception] = None):
        self.position = position
        self.result = result
        self.default = default
        self.argument = argument
        self.error = error

    def __bool__(self):
        return bool(self.value)

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
        converter, default = unpack_varargs(item, ('converter', 'default'), default=None)

        @classmethod
        async def convert(_, ctx: Context, arg: str):
            pos = ctx.view.previous
            try:
                result = await ctx.command._actual_conversion(ctx, converter, arg, cls)
                return cls(pos, result, argument=arg)
            except CommandError as e:
                ctx.view.undo()
                return cls(pos, default=default, argument=arg, error=e)

        __dict__ = {'convert': convert, 'default': default, '_converter': converter}
        return Union[type(cls.__name__, (Maybe,), __dict__), None]

    @classmethod
    def asdict(cls, **items: Maybe[R]) -> dict[str, R]:
        return defaultdict(lambda: None, {
            k: v.value if isinstance(v, cls) else v for k, v in items.items()
            if not isinstance(v, cls) or v.value is not None
        })

    @classmethod
    def astuple(cls, *items: Maybe[R]) -> tuple[R, ...]:
        return tuple(v.value if isinstance(v, cls) else v for v in items)

    @classmethod
    def errordict(cls, **items: Maybe) -> dict[str, Exception]:
        errors = {}
        for k, v in items.items():
            if isinstance(v, cls) and v.error is not None:
                errors[k] = v.error
        return errors

    @classmethod
    def unpack(cls, **items: Maybe[R]) -> tuple[dict[str, R], dict[str, Exception]]:
        return cls.asdict(**items), cls.errordict(**items)

    @classmethod
    def reconstruct(cls, *items: Optional[Maybe]) -> str:
        args: list[str] = []
        last_index = 0
        for item in items:
            if item is None or not isinstance(item, cls):
                continue
            arg = item.argument
            if arg is None:
                continue
            arg = str(arg)
            if last_index != item.position:
                args.append(arg)
                last_index = item.position
            else:
                if args:
                    args.pop()
                args.append(arg)
        return ' '.join(args)
