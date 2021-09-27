# osm.py
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
from typing import Optional

from aiohttp import ClientSession
from discord.ext.commands import (BucketType, Converter, command, cooldown,
                                  max_concurrency)
from discord.ext.commands.errors import BadArgument
from django.conf import settings
from geopy import Location, Point
from geopy.adapters import AioHTTPAdapter
from geopy.geocoders import Nominatim

from ...context import Circumstances
from ...ext.autodoc import accepts
from ...utils.markdown import code, verbatim


def parse_point_no_warn(s: str):
    """Parse a geopy.Point with all warnings suppressed."""
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', category=UserWarning)
        return Point.from_string(s)


def parse_point_strict_exc(s: str):
    """Parse a geopy.Point, raising all warnings as exceptions."""
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings('error', category=UserWarning)
            return Point.from_string(s)
    except UserWarning as e:
        raise ValueError from e


@accepts('latitude', predicative=f'such as {code(-41.5)}, {code("41.5N")}, or {code("N 39°")}')
class Latitude(Converter, float):
    """Convert a string to a float representing a latitude.

    Accepts a regular floating-point number and the degree-minute-second notation.
    Ensures the number is within a valid range (-90 to 90).
    """

    def __init__(self) -> None:
        pass

    async def convert(self, ctx: Circumstances, argument: str) -> float:
        try:
            point = parse_point_no_warn(f'{argument} 0')
            return point.latitude
        except ValueError:
            raise BadArgument(f'Failed to parse {verbatim(argument)} as a latitude')


@accepts('longitude', predicative=f'such as {code(-110)}, {code("30E")}, or {code("E 162°")}')
class Longitude(Converter, float):
    """Convert a string to a float representing a latitude.

    Accepts a regular floating-point number and the degree-minute-second notation.
    Ensures the number is within a valid range (0 to 180).
    """

    def __init__(self) -> None:
        pass

    async def convert(self, ctx: Circumstances, argument: str) -> float:
        try:
            point = parse_point_no_warn(f'0 {argument}')
            return point.longitude
        except ValueError:
            raise BadArgument(f'Failed to parse {verbatim(argument)} as a longitude')


class ManagedAioHTTPAdapter(AioHTTPAdapter):
    """Subclass of geopy.AioHTTPAdapter allowing sessions to be removed."""

    @property
    def session(self):
        """The aiohttp.ClientSession associated with this adapter."""
        return super().session

    @session.setter
    def session(self, ses: ClientSession):
        self.__dict__['session'] = ses

    @session.deleter
    def session(self):
        self.__dict__.pop('session', None)


def make_geolocator(session: Optional[ClientSession] = None) -> Nominatim:
    """Initialize a default geolocator using the Nominatim API."""
    locator = Nominatim(
        timeout=10, user_agent=settings.USER_AGENT,
        adapter_factory=ManagedAioHTTPAdapter,
    )
    locator.adapter.session = session
    return locator


def format_coarse_location(location: Location) -> str:
    """Create a string representation of a geopy.Location that is at most city-level precise."""
    info: dict = location.raw.get('address', {})
    levels = [
        ('country', 'country_code', 'continent'),
        ('state', 'state_district', 'province', 'region', 'county'),
        ('city', 'municipality', 'town', 'village', 'locality'),
    ]
    segments = [[*filter(None, (info.get(k) for k in tags))] for tags in levels]
    segments = [s[0] for s in segments if s]
    return ', '.join(reversed(segments))


@command('!tzlocation', hidden=True)
@max_concurrency(1, BucketType.guild, wait=True)
@cooldown(1, 5, BucketType.default)
async def get_location(ctx, **kwargs) -> Location | list[Location]:
    """Private Command object for making requests to the Nominatim API.

    The command has a concurrency limit and a cooldown. This allows
    users of the function to prevent excessive API calls on the
    end user level by triggering the cooldown and concurrency.
    """
    geolocator = make_geolocator(ctx.session)
    return await geolocator.geocode(**kwargs)
