# bot.py
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

from typing import Optional

import pytz
from discord import Member
from geopy import Location, Point
from geopy.exc import GeocoderTimedOut

from ts2.utils.datetime import utcnow

from .. import documentation as doc
from ..command import ensemble, instruction
from ..context import Circumstances
from ..converters.functional import RetainsError
from ..documentation import NotAcceptable
from ..extension import Gear
from ..models import User
from ..services import ServiceUnavailable
from ..services.osm import get_location
from ..services.tz import Latitude, Longitude, Timezone, tzfinder
from ..utils.duckcord.embeds import Embed2
from ..utils.markdown import code, verbatim


class Conf(
    Gear, name='Settings', order=30,
    description='Commands for personalization',
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @instruction('gdpr', aliases=('export',))
    @doc.description('Get a copy of everything the bot knows about you via DM.')
    async def gdpr(self, ctx: Circumstances):
        pass

    @instruction('me', invoke_without_command=True)
    @doc.description('Print your settings within the bot.')
    async def me(self, ctx: Circumstances):
        profile: User = await User.aget(ctx.author)

        footer = ('No preference set, showing default values'
                  if profile.isdefault else None)
        info = profile.format_prefs()
        lines = []
        res = (
            Embed2(title='Settings', description='\n'.join(lines))
            .set_footer(text=footer)
            .set_timestamp()
            .personalized(ctx.author)
        )
        for k, v in info.items():
            res = res.add_field(name=k, value=code(v or '(none)'), inline=True)
        return await ctx.reply(embed=res)

    @ensemble('my', aliases=('conf',))
    @doc.description('Configure various preferences.')
    @doc.hidden
    async def conf(self, ctx: Circumstances):
        pass

    @conf.instruction('timezone', aliases=('tz',))
    @doc.description('Set timezone preference.')
    @doc.argument('tz', 'Timezone to set.')
    @doc.argument('latitude', 'Latitude of the location whose timezone to use.')
    @doc.argument('longitude', 'Longitude of the location whose timezone to use.')
    @doc.argument('location', 'Name of a location to search for.')
    @doc.use_syntax_whitelist
    @doc.invocation((), 'Print your current timezone setting.')
    @doc.invocation(('tz',), 'Set your timezone using an IANA timezone code.')
    @doc.invocation(('latitude', 'longitude'), 'Set your timezone using a coordinate.')
    @doc.invocation(('location',), 'Set your timezone by searching for a location.')
    @doc.discussion('Privacy', ('When setting timezones using lat/long or a location query,'
                                ' your message will be immediately deleted.\n'
                                'The bot does not keep your location info.'))
    @RetainsError.ensure
    async def timezone(
        self, ctx: Circumstances,
        tz: RetainsError[Timezone, None],
        latitude: RetainsError[Latitude, None],
        longitude: RetainsError[Longitude, None],
        *, location: RetainsError[str, None],
    ):
        author = ctx.author
        values, errors = RetainsError.unpack(
            tz=tz, latitude=latitude,
            longitude=longitude, location=location,
        )

        if not errors and not values:
            profile: User = await User.aget(author)
            if profile.timezone:
                body = code(profile.timezone)
            else:
                body = 'No timezone preference set.'
            return await ctx.reply(embed=Embed2(
                title='Timezone',
                description=body,
            ).personalized(author))

        tz = values['tz']
        if tz is not None:
            profile = await self.set_tz(author, tz)
            res = self.fmt_tz_set(profile, tz).personalized(author)
            return await ctx.reply(embed=res)

        query: Optional[str] = values['location']
        lat: Optional[float] = values['latitude']
        long: Optional[float] = values['longitude']
        raw_input = ctx.raw_input

        if query is None:
            if lat is not None and long is not None:
                tzname = tzfinder.timezone_at(lng=long, lat=lat)
                tz = pytz.timezone(tzname)
                profile = await self.set_tz(author, tz)
                res = self.fmt_tz_set(profile, tz).personalized(author)
                await ctx.message.delete(delay=0.1)
                return await ctx.pingback(embed=res)

        bad_coord = None
        try:
            point = Point.from_string(raw_input)
        except ValueError:
            if lat is not None and long is not None:
                pass
            elif lat is not None:
                bad_coord = (
                    f'successfully parsed latitude {lat:.3f}'
                    ' but longitude not found or cannot be parsed.'
                )
            elif long is not None:
                bad_coord = (
                    f'successfully parsed longitude {long:.3f}'
                    ' but latitude not found or cannot be parsed.'
                )
        else:
            tz = tzfinder.timezone_at(lng=point.longitude, lat=point.latitude)
            return await ctx.send((tz, point))

        query = raw_input
        async with ctx.typing():
            try:
                place: list[Location] = await ctx.call(
                    get_location, query=raw_input,
                    addressdetails=True,
                )
            except GeocoderTimedOut:
                raise ServiceUnavailable('Searching on OpenStreetMap took too long.')

        if not place:
            msg = f'Failed to find a location on OpenStreetMap using {verbatim(query)}'
            if bad_coord:
                msg = f'{msg}\nAdditionally, {bad_coord}'
            raise NotAcceptable(msg)

        point = place.point
        tzname = tzfinder.timezone_at(lng=point.longitude, lat=point.latitude)
        tz = pytz.timezone(tzname)
        profile = await self.set_tz(author, tz)
        res = self.fmt_tz_set(profile, tz).personalized(author)
        locationstr = self.fmt_coarse_location(place)
        if locationstr:
            res = res.add_field(name='Location', value=locationstr)
        await ctx.message.delete(delay=0.1)
        return await ctx.pingback(embed=res)

    async def set_tz(self, member: Member, tz: pytz.BaseTzInfo):
        profile: User = await User.aget(member)
        await profile.save_timezone(tz)
        return profile

    def fmt_tz_set(self, user: User, tz: pytz.BaseTzInfo) -> Embed2:
        dt = utcnow().astimezone(tz)
        zonename = tz.tzname(dt.replace(tzinfo=None)) or '(unknown)'
        dtstr = f'{user.format_datetime(dt)}'
        return (
            Embed2(title=f'Timezone set: {zonename}')
            .add_field(name='Local time', value=dtstr)
            .set_footer(text=f'IANA tz code: {tz}')
        )

    def fmt_coarse_location(self, location: Location) -> str:
        info: dict = location.raw.get('address', {})
        levels = [
            ('country', 'country_code', 'continent'),
            ('state', 'state_district', 'region', 'county'),
            ('city', 'municipality', 'town', 'village'),
        ]
        segments = [[*filter(None, (info.get(k) for k in tags))] for tags in levels]
        segments = [s[0] for s in segments if s]
        return ', '.join(reversed(segments))
