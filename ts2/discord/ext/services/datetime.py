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

from datetime import datetime, timedelta

import pytz
from discord.ext.commands import Converter
from discord.ext.commands.errors import BadArgument
from discord.utils import escape_markdown
from timezonefinder import TimezoneFinder

from ...context import Circumstances
from ...ext.autodoc import accepts
from ...utils.markdown import a, code

tzfinder = None
tznames: dict[str, pytz.BaseTzInfo] = {}


def get_tzfinder() -> TimezoneFinder:
    global tzfinder
    if tzfinder is None:
        tzfinder = TimezoneFinder(in_memory=True)
    return tzfinder


def make_tz_names():
    year = datetime.now().year
    time_1 = datetime(year, 1, 1)
    time_2 = datetime(year, 6, 1)
    for iana in pytz.common_timezones:
        tz = pytz.timezone(iana)
        tznames[tz.tzname(time_1)] = tz
        tznames[tz.tzname(time_2)] = tz


def get_tz_by_name(s: str) -> pytz.BaseTzInfo:
    if not tznames:
        make_tz_names()
    return tznames[s]


def is_ambiguous_static_tz(tz: pytz.BaseTzInfo) -> bool:
    return (not hasattr(tz, '_tzinfos')
            and getattr(tz, '_utcoffset') != timedelta(0))


@accepts('IANA tz code', predicative=(
    f'see {a("list of timezones", "https://en.wikipedia.org/wiki/List_of_tz_database_time_zones")}'
))
class Timezone(Converter, pytz.BaseTzInfo):
    def __init__(self) -> None:
        pass

    async def convert(self, ctx: Circumstances, argument: str) -> pytz.BaseTzInfo:
        try:
            tz = pytz.timezone(argument)
            if not is_ambiguous_static_tz(tz):
                return tz
        except pytz.UnknownTimeZoneError:
            pass
        try:
            return get_tz_by_name(argument)
        except KeyError:
            raise BadArgument(f'Unknown timezone {code(escape_markdown(argument))}')
