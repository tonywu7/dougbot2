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
from typing import Generic, Optional, TypeVar, Union, get_args

from discord.ext.commands import Context, Converter
from discord.ext.commands.errors import MissingRequiredArgument

from ...utils.parsers.structural import get_live_converter
from .utils import unpack_varargs

T = TypeVar("T")
U = TypeVar("U")
R = TypeVar("R")


class Maybe(Converter, Generic[T, U]):
    """Converter wrapper that retains conversion errors and never fails.

    Maybe implements `__class_getitem__`. Use it with another converter:
    instead of:

        async def command(ctx, number: int)

    Annotate the function like:

        async def command(ctx, number: Maybe[int])

    The command will receive a `Maybe` object containing the converted value
    if conversion succeeded, or the error if it failed.

    The `convert` method here delegate the actual conversion task to
    the `Context` object; thus it should be compatible with all converters
    (including `Union`, `Optional`, and `Greedy`).
    """

    name = "<param>"
    _converter: type

    def __init__(
        self,
        position: int = 0,
        result: T = Parameter.empty,
        default: U = Parameter.empty,
        argument: Optional[str] = None,
        errors: list[Exception] = None,
    ):
        self.position = position
        self.result = result
        self.default = default
        self.argument = argument
        self.errors = errors or []

    def __bool__(self):
        return bool(self.value)

    @property
    def value(self):
        """The result of the conversion, if any.

        :raises ValueError: if conversion failed.
        """
        if self.result is not Parameter.empty:
            return self.result
        elif self.default is not Parameter.empty:
            return self.default
        raise ValueError

    @classmethod
    def ensure(cls, f):
        """Decorate a command callback such that arguments annotated with `Maybe`\
        are guaranteed to receive a `Maybe` instance even if that argument is not\
        provided in the message (with appropriate default values).

        Due to the way discord.py's argument parsing is implemented, missing optional
        arguments are automatically filled with their default values as defined
        in the function signature. The resulting wrapper from this decorator
        processes all the arguments first before passing it to the actual command callback.
        """
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

    def __class_getitem__(cls, item):
        annotation, default = unpack_varargs(
            item, ("annotation", "default"), default=None
        )
        convertf = get_live_converter(annotation, default)

        @classmethod
        async def convert(_, ctx: Context, arg: str):
            pos = ctx.view.previous
            errors = []
            result = await convertf(ctx, arg, errors)
            if errors:
                ctx.view.undo()
            return cls(pos, result, argument=arg, errors=errors)

        __dict__ = {"convert": convert, "default": default, "_converter": annotation}
        return Union[type(cls.__name__, (Maybe,), __dict__), None]

    @classmethod
    def asdict(cls, **items: Maybe[R]) -> dict[str, R]:
        """Unwrap all successfully parsed `Maybe` instances and return the results as a mapping.

        This is semantically similar to Django form's `cleaned_data` attribute.
        """
        return defaultdict(
            lambda: None,
            {
                k: v.value if isinstance(v, cls) else v
                for k, v in items.items()
                if not isinstance(v, cls) or v.value is not None
            },
        )

    @classmethod
    def astuple(cls, *items: Maybe[R]) -> tuple[R, ...]:
        """Unwrap all successfully parsed `Maybe` instances and return the results as a tuple."""
        return tuple(v.value if isinstance(v, cls) else v for v in items)

    @classmethod
    def errordict(cls, **items: Maybe) -> dict[str, list[Exception]]:
        """Unwrap all failed `Maybe` instances and return the exceptions as a mapping.

        This is semantically similar to Django form's `errors` attribute.
        """
        errors = {}
        for k, v in items.items():
            if isinstance(v, cls) and v.errors:
                errors[k] = [*v.errors]
        return errors

    @classmethod
    def unpack(
        cls, **items: Maybe[R]
    ) -> tuple[dict[str, R], dict[str, list[Exception]]]:
        """Unwrap all `Maybe` instances and return the results and exceptions as mappings."""
        return cls.asdict(**items), cls.errordict(**items)

    @classmethod
    def reconstruct(cls, *items: Optional[Maybe]) -> str:
        """Reconstruct the command invocation (as a string) from `Maybe` objects."""
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
        return " ".join(args)

    def __repr__(self):
        return (
            f"<Maybe: arg={repr(self.argument)}"
            f" result={self.result}"
            f" error={bool(self.errors)}>"
        )

    __str__ = __repr__
