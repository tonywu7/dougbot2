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

from typing import Optional

from aiohttp import ClientSession
from discord.ext.commands import BucketType, command, cooldown, max_concurrency
from django.conf import settings
from geopy import Location
from geopy.adapters import AioHTTPAdapter
from geopy.geocoders import Nominatim


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


@command('!tzlocation', hidden=True)
@max_concurrency(1, BucketType.guild, wait=True)
@cooldown(1, 5, BucketType.default)
async def get_location(ctx, **kwargs) -> Location | list[Location]:
    geolocator = make_geolocator(ctx.session)
    return await geolocator.geocode(**kwargs)
