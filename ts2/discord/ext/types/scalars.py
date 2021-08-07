# scalars.py
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

from datetime import datetime, timedelta
from typing import Union

from dateparser import parse as parse_date
from discord.ext.commands import BadArgument, Converter
from discord.utils import escape_markdown

from ...utils.datetime import strpduration
from ...utils.markdown import code
from ..autodoc.decorators import accepts


@accepts('duration', predicative=f'such as {code("60s")}, {code("1h13m36s")}, or {code("3w6d")}')
class Timedelta(Converter):
    value: timedelta

    async def convert(self, ctx, argument: Union[str, timedelta]):
        if isinstance(argument, timedelta):
            return argument
        self.value = strpduration(argument)
        return self


@accepts('date/time')
class Datetime(Converter):
    value: datetime

    async def convert(self, ctx, argument: Union[str, datetime]):
        if isinstance(argument, datetime):
            return argument
        dt = parse_date(argument)
        if not dt:
            raise BadArgument(f'Cannot parse {code(escape_markdown(argument))} as a date/time.')
        self.value = dt
        return self
