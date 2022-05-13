# datetime.py
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
from typing import Optional, Union

import pytz
from dateparser import parse as parse_date
from discord.ext.commands import BadArgument, Converter
from discord.utils import escape_markdown

from ..datetime import get_tz_by_name, is_ambiguous_static_tz, strpduration
from ..markdown import code


class Timedelta(Converter):
    """Convert a duration string to a timedelta object.

    Converter returns itself.
    """

    value: timedelta

    async def convert(self, ctx, argument: Union[str, timedelta]):
        if isinstance(argument, timedelta):
            return argument
        self.value = strpduration(argument)
        return self


class Datetime(Converter):
    """Convert a date and time string to a datetime object.

    Uses `dateparser.parse`. Returns itself.
    """

    value: datetime

    async def convert(self, ctx, argument: Union[str, datetime]):
        if isinstance(argument, datetime):
            return argument
        dt = parse_date(argument)
        if not dt:
            raise BadArgument(
                f"Cannot parse {code(escape_markdown(argument))} as a date/time."
            )
        self.value = dt
        return self


class Timezone(Converter):
    """Convert a string to a pytz TzInfo object from either a valid IANA timezone code\
    or a commonly seen timezone abbreviations, such as "EST"."""

    def __init__(self) -> None:
        pass

    value: pytz.BaseTzInfo

    @classmethod
    def get_timezone_from_name(cls, name: str) -> Optional[pytz.BaseTzInfo]:
        try:
            tz = pytz.timezone(name)
            if not is_ambiguous_static_tz(tz):
                return tz
        except pytz.UnknownTimeZoneError:
            pass
        try:
            return get_tz_by_name(name)
        except KeyError:
            return None

    async def convert(self, ctx, argument: str):
        tz = self.get_timezone_from_name(argument)
        if tz is None:
            raise BadArgument(f"Unknown timezone {code(escape_markdown(argument))}")
        self.value = tz
        return self
