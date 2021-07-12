# tz.py
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

import warnings

import pytz
from discord.ext.commands import Converter
from discord.ext.commands.errors import BadArgument
from discord.utils import escape_markdown
from geopy import Point
from timezonefinder import TimezoneFinder

from ..context import Circumstances
from ..documentation import accepts
from ..utils.markdown import a, code, verbatim

tzfinder = None


def get_tzfinder() -> TimezoneFinder:
    global tzfinder
    if tzfinder is None:
        tzfinder = TimezoneFinder(in_memory=True)
    return tzfinder


@accepts('IANA tz code', predicative=(
    f'see {a("https://en.wikipedia.org/wiki/List_of_tz_database_time_zones", "list of timezones")}'
))
class Timezone(Converter, pytz.BaseTzInfo):
    def __init__(self) -> None:
        pass

    async def convert(self, ctx: Circumstances, argument: str) -> pytz.BaseTzInfo:
        try:
            return pytz.timezone(argument)
        except pytz.UnknownTimeZoneError:
            raise BadArgument(f'Unknown timezone {code(escape_markdown(argument))}')


@accepts('latitude', predicative=f'such as {code(-41.5)}, {code("41.5N")}, or {code("N 39°")}')
class Latitude(Converter, float):
    def __init__(self) -> None:
        pass

    async def convert(self, ctx: Circumstances, argument: str) -> float:
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(category=UserWarning)
                point = Point.from_string(f'{argument} 0')
            return point.latitude
        except ValueError:
            raise BadArgument(f'Failed to parse {verbatim(argument)} as a latitude')


@accepts('longitude', predicative=f'such as {code(-110)}, {code("30E")}, or {code("E 162°")}')
class Longitude(Converter, float):
    def __init__(self) -> None:
        pass

    async def convert(self, ctx: Circumstances, argument: str) -> float:
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(category=UserWarning)
                point = Point.from_string(f'0 {argument}')
            return point.longitude
        except ValueError:
            raise BadArgument(f'Failed to parse {verbatim(argument)} as a longitude')
