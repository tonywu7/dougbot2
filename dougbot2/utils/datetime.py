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
from datetime import datetime, timedelta, timezone

import pytz
from django.utils.timezone import get_current_timezone
from timezonefinder import TimezoneFinder

RE_DURATION = re.compile(r"(?P<num>[0-9]+)\s*?(?P<unit>(y|mo|w|d|h|m|s?))")


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
    # TODO: support negative duration?
    """Convert strings representing a duration to a `timedelta` object.

    Examples are `90s`, `1m30s`, `7d`, etc.

    Parsing is lenient: the function will consider any number followed by
    any word beginning with any of the possible units as part of
    the duration, thus the following will all return a non-zero duration:

        7 yes, 5 moments, 4d6d9y

    """
    seconds = 0
    unit = {
        "y": 31536000,
        "mo": 2592000,
        "w": 604800,
        "d": 86400,
        "h": 3600,
        "m": 60,
        "s": 1,
        "": 1,
    }
    for seg in RE_DURATION.finditer(s):
        seconds += int(seg["num"]) * unit[seg["unit"]]
    return timedelta(seconds=seconds)


def assumed_utc(d: datetime) -> datetime:
    """Assume this datetime (maybe naive) has a value representing a time in UTC\
    and return an aware datetime."""
    return d.replace(tzinfo=timezone.utc)


tzfinder = None
tznames: dict[str, pytz.BaseTzInfo] = {}


def get_tzfinder() -> TimezoneFinder:
    global tzfinder
    if tzfinder is None:
        tzfinder = TimezoneFinder(in_memory=True)
    return tzfinder


def make_tz_names():
    """Generate a mapping of common timezone abbreviations (including DSTs) to non-DST tz objects.

    For example, both `'EST'` and `'EDT'` will map to the US/Eastern TzInfo.
    """
    year = datetime.now().year
    time_1 = datetime(year, 1, 1)
    time_2 = datetime(year, 6, 1)
    for iana in pytz.common_timezones:
        tz = pytz.timezone(iana)
        tznames[tz.tzname(time_1)] = tz
        tznames[tz.tzname(time_2)] = tz


def get_tz_by_name(s: str) -> pytz.BaseTzInfo:
    """Get TzInfo by a possible timezone abbreviation."""
    if not tznames:
        make_tz_names()
    try:
        return tznames[s]
    except KeyError:
        return tznames[s.upper()]


def fuzzy_tz_names(query: str) -> list[str]:
    """Attempt to find timezone abbreviations similar to this string (using fuzzy match)."""
    if not tznames:
        make_tz_names()
    try:
        from rapidfuzz import process as fuzzy
        from rapidfuzz.fuzz import QRatio
    except ModuleNotFoundError:
        return []
    else:
        matched = fuzzy.extract(query, tznames.keys(), scorer=QRatio, score_cutoff=65)
    return [match_ for match_, score in matched]


def is_ambiguous_static_tz(tz: pytz.BaseTzInfo) -> bool:
    """Return True if this TzInfo object has no DST info but the region it represents has DST.

    Such TzInfo objects are considered "ambiguous" because it is impossible to localize
    a datetime with them.
    """
    return not hasattr(tz, "_tzinfos") and getattr(tz, "_utcoffset") != timedelta(0)
