# structured.py
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

import simplejson
import toml
from discord.ext.commands import Converter
from discord.ext.commands.errors import BadArgument

from ..autodoc import accepts


@accepts('TOML code block', concise='TOML', uncountable=True)
class CodeBlockParser(Converter):
    lang: str

    @classmethod
    def parse(cls, text: str):
        raise NotImplementedError

    @classmethod
    def prepare(cls, text: str) -> str:
        text = text.strip()
        lang = cls.lang
        sig = f'```{lang}'
        if not text.startswith(f'{sig}\n'):
            raise BadArgument(f'Code block does not begin with {sig}')
        if not text.endswith('\n```'):
            raise BadArgument('Code block does not end with ```')
        return text.removeprefix(f'{sig}\n').removesuffix('```')

    async def convert(self, ctx, arg: str):
        self.result = self.parse(self.prepare(arg))
        return self


class TOML(CodeBlockParser):
    lang = 'toml'
    result: dict

    @classmethod
    def parse(cls, text: str):
        try:
            return toml.loads(text)
        except toml.TomlDecodeError:
            raise BadArgument('Not a valid TOML markup.')


class JSON(CodeBlockParser):
    lang = 'json'
    result: dict

    @classmethod
    def parse(cls, text: str):
        try:
            return simplejson.loads(text)
        except toml.TomlDecodeError:
            raise BadArgument('Not a valid JSON.')
