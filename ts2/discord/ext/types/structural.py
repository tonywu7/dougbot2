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

from collections.abc import Mapping
from typing import TypeVar, Union

import simplejson as json
import toml
from discord.ext.commands import Context, Converter
from discord.ext.commands.view import StringView

from ...utils.markdown import find_codeblock
from ..autodoc.decorators import accepts

T = TypeVar('T')


class CodeBlock(Converter):
    langs: tuple[str, ...]
    exc: tuple[type[Exception], ...]

    def parse(self, code: str):
        raise NotImplementedError

    async def convert(self, ctx: Context, argument: str):
        view: StringView = ctx.view
        buffer = view.buffer[view.previous:]
        code, length = find_codeblock(buffer, self.langs)
        if not code:
            raise ValueError(f'Not a valid {self.langs[0]} code block.')
        try:
            self.result = self.parse(code)
        except self.exc as e:
            raise ValueError(f'Not a valid {self.langs[0]} code block: {e}')
        view.index = view.previous + length
        return self


@accepts('JSON code block')
class JSON(CodeBlock):
    langs = ('json',)
    exc = (json.JSONDecodeError,)
    result: dict

    def parse(self, code: str):
        return json.loads(code)


@accepts('TOML code block')
class TOML(CodeBlock):
    langs = ('toml',)
    exc = (toml.TomlDecodeError,)
    result: dict

    def parse(self, code: str):
        return toml.loads(code)


@accepts('dict object')
class _Dictionary(Converter):
    async def convert(self, ctx, argument):
        if isinstance(argument, dict):
            return argument
        raise ValueError('Not a dictionary.')


@accepts('Jinja code block')
class JinjaTemplate(CodeBlock):
    langs = ('jinja',)
    exc = (Exception,)
    result: str

    def parse(self, code: str):
        return code


Dictionary = Union[_Dictionary, TOML, JSON]


def unpack_dict(d: Dictionary, default: T = None) -> Union[Mapping, T]:
    if isinstance(d, Mapping):
        return d
    if isinstance(d, (TOML, JSON)):
        return d.result
    return default
