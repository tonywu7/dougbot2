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

import re
from datetime import datetime, timezone, timedelta

from django.utils.timezone import get_current_timezone

RE_DURATION = re.compile(r'(?P<num>[0-9]+)\s*?(?P<unit>(y|mo|w|d|h|m|s?))')


def localnow() -> datetime:
    """Return an aware `datetime` set to current local time, per Django settings."""
    return datetime.now(tz=get_current_timezone())


def utcnow() -> datetime:
    """Return an aware `datetime` set to current UTC time."""
    return datetime.now(tz=timezone.utc)


def utctimestamp() -> float:
    """Return the current POSIX UTC timestamp."""
    return datetime.now(tz=timezone.utc).timestamp()


def strpduration(s: str) -> timedelta:
    seconds = 0
    unit = {
        'y': 31536000,
        'mo': 2592000,
        'w': 604800,
        'd': 86400,
        'h': 3600,
        'm': 60,
        's': 1,
        '': 1,
    }
    for seg in RE_DURATION.finditer(s):
        seconds += int(seg['num']) * unit[seg['unit']]
    return timedelta(seconds=seconds)


def assumed_utc(d: datetime) -> datetime:
    return d.replace(tzinfo=timezone.utc)
