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


class ManagedAioHTTPAdapter(AioHTTPAdapter):
    @property
    def session(self):
        return super().session

    @session.setter
    def session(self, ses: ClientSession):
        self.__dict__['session'] = ses

    @session.deleter
    def session(self):
        self.__dict__.pop('session', None)


def make_geolocator(session: Optional[ClientSession] = None) -> Nominatim:
    locator = Nominatim(
        timeout=10, user_agent=settings.USER_AGENT,
        adapter_factory=ManagedAioHTTPAdapter,
    )
    locator.adapter.session = session
    return locator


def format_coarse_location(location: Location) -> str:
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
    geolocator = make_geolocator(ctx.session)
    return await geolocator.geocode(**kwargs)
