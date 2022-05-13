# structural.py
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

from collections import defaultdict
from inspect import Parameter
from typing import Optional, Union, get_args, get_origin

import simplejson as json
import toml
from discord.ext.commands import Command, CommandError, Context, MissingRequiredArgument
from discord.ext.commands.converter import _Greedy
from discord.ext.commands.view import StringView

from ..markdown import unwrap_codeblock


def _is_type_union(annotation) -> bool:
    return get_origin(annotation) is Union  # type: ignore


def _is_optional_type(annotation) -> bool:
    return type(None) in get_args(annotation)


def _is_greedy(annotation) -> bool:
    return isinstance(annotation, _Greedy)


def get_live_converter(annotation, default):
    """Get a discord.py-compatible converter function based on the annotation object.

    The returning function is for either a regular type, or a union type
    (the `Union` converter), or the `Greedy` converter.
    """

    if annotation is Parameter.empty:
        raise StructuralParsingError()

    _placeholder = Parameter("_", Parameter.POSITIONAL_OR_KEYWORD)

    if _is_greedy(annotation):

        elem_conv = get_live_converter(annotation.converter, default)

        async def convert(ctx: Context, args: list, errorlist: Optional[list] = None):
            results = []
            for item in args:
                try:
                    converted = await elem_conv(ctx, item)
                    if converted is not Parameter.empty:
                        results.append(converted)
                except CommandError as exc:
                    if errorlist is not None:
                        errorlist.append(exc)
            return results

    elif _is_type_union(annotation):

        async def convert(ctx: Context, arg, errorlist: Optional[list] = None):
            cmd: Command = ctx.command
            _convertf = cmd._actual_conversion
            for conv in annotation.__args__:
                if conv is type(None):  # noqa: E721
                    return default
                try:
                    return await _convertf(ctx, conv, arg, _placeholder)
                except CommandError as exc:
                    if errorlist is not None:
                        errorlist.append(exc)
            return default

    else:

        async def convert(ctx: Context, arg, errorlist: Optional[list] = None):
            cmd: Command = ctx.command
            _convertf = cmd._actual_conversion
            try:
                return await _convertf(ctx, annotation, arg, _placeholder)
            except CommandError as exc:
                errorlist.append(exc)
                return default

    return convert


class StructuredView(StringView):
    """Emulation of discord.py's StringView that has its content already parsed and structured."""

    def __init__(self, items: list):
        self.items = [str(i) for i in items]
        self.idx = 0
        self.buffer = " ".join(self.items)
        self.end = len(self.buffer)

    @property
    def index(self) -> int:
        return len(" ".join(self.items[: self.idx + 1]))

    @property
    def previous(self) -> int:
        return len(" ".join(self.items[: self.idx]))

    @property
    def current(self):
        return self.items[self.idx]

    @property
    def eof(self):
        return False

    def undo(self):
        return

    def skip_ws(self):
        return

    def skip_string(self, string):
        return False

    def read_rest(self):
        return " ".join(self.items[self.idx :])

    def read(self, n):
        return self.current[:n]

    def get(self):
        return self.current[0]

    def get_word(self):
        return self.current

    def get_quoted_word(self):
        return self.current

    def forward(self):
        if self.idx + 1 == len(self.items):
            return
        self.idx += 1


class StructuralArgumentParser:
    """Parse command arguments sent as structured text: TOML or JSON.

    Instead of putting command arguments on the same line in order,
    this allows people to specify arguments like a form, and reducing
    the likelihood of incorrect quotation (because quotation is not
    a concept most ordinary users are familiar with).

    Thus, for example, for a command that takes arguments `channel`,
    `role`, and `user`, instead of writing:

        command #channel @role @user

    It is possible to write:

        command ```toml
        role = 'role'
        user = 'user'
        channel = 'channel'
        ```

    This makes it significantly easier to write complex commands.
    """

    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.params: dict[str, Parameter] = {}
        self.args: dict = {}
        self.errors = defaultdict(list)
        for k, v in [*ctx.command.params.items()][1:]:
            if isinstance(v.annotation, type) and issubclass(v.annotation, Context):
                continue
            self.params[k] = v

    def get_raw_input(self):
        """Retrieve everything after the prefix and command from the message."""

        ctx = self.ctx
        full_invoked_with = " ".join(
            {
                **{k: True for k in ctx.invoked_parents},
                ctx.invoked_with: True,
            }.keys()
        )
        msg: str = ctx.view.buffer
        return msg.removeprefix(ctx.prefix).strip()[len(full_invoked_with) :].strip()

    def loads(self) -> Optional[dict]:
        """Try to find and load a JSON/TOML string."""
        text = self.get_raw_input()
        data: Optional[dict] = None
        for lang, loader, exceptions in [
            ("toml", toml.loads, (toml.TomlDecodeError,)),
            ("json", json.loads, (json.JSONDecodeError,)),
        ]:
            if data is not None:
                break
            try:
                code = unwrap_codeblock(text, lang)
                data = loader(code)
            except (ValueError, *exceptions):
                continue
        return data

    def default_args(self):
        """Prepare the default argument array, depending on\
        whether the command is from a cog."""
        cmd = self.ctx.command
        if cmd.cog is None:
            return [self.ctx]
        else:
            return [cmd.cog, self.ctx]

    def apply(self):
        """Populate the context's args and kwargs using the parsed result."""
        args = self.ctx.args = self.default_args()
        kwargs = self.ctx.kwargs
        for k, v in self.params.items():
            parsed = self.args.pop(k)
            if parsed is Parameter.empty:
                if _is_greedy(v.annotation):
                    parsed = []
                elif _is_optional_type(v.annotation):
                    parsed = None
                elif v.kind is Parameter.VAR_KEYWORD:
                    continue
                else:
                    errors = self.errors.get(k)
                    if errors:
                        raise errors[0]
                    raise MissingRequiredArgument(v)
            if v.kind is Parameter.POSITIONAL_ONLY:
                args.append(parsed)
            else:
                kwargs[k] = parsed

    async def parse(self):
        """Attempt to parse the dictionary and convert all values to their expected types.

        This essentially replicates discord.py's parsing process, except string scanning
        is not necessary.
        """
        data = self.loads()
        if data is None:
            raise StructuralParsingError()
        view = self.ctx.view
        self.ctx.view = tempview = StructuredView(data.values())
        try:
            for k, v in self.params.items():
                try:
                    value = data.pop(k)
                except KeyError:
                    self.args[k] = v.default
                    continue
                errorlist = self.errors[k]
                annotation = v.annotation
                default = v.default
                converter = get_live_converter(annotation, default)
                result = await converter(self.ctx, value, errorlist)
                self.args[k] = result
                tempview.forward()
        finally:
            self.ctx.view = view

    async def __call__(self):
        """Run the parser on this message and populate the arguments."""
        await self.parse()
        self.apply()


class StructuralParsingError(Exception):
    """Exception for when the message does not contain a valid TOML/JSON string."""

    pass
