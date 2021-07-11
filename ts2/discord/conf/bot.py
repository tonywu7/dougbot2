# bot.py
# Copyright (C) 2021  Tony Wu +https://github.com/tonywu7/
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

from discord.ext.commands import BucketType, cooldown

from .. import documentation as doc
from ..command import ensemble, instruction
from ..context import Circumstances
from ..converters import RetainsError, Timezone
from ..extension import Gear
from ..models import User
from ..utils.duckcord.embeds import Embed2
from ..utils.markdown import code


class Conf(
    Gear, name='Settings', order=30,
    description='Commands for personalization',
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @ensemble('conf', aliases=('my',), invoke_without_command=True)
    @doc.description('Print your settings within the bot.')
    async def conf(self, ctx: Circumstances):
        profile: User = await User.aget(ctx.author.id)

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
    @doc.invocation(('location',), 'Set your timezone by looking up a location.')
    @RetainsError.ensure
    async def timezone(
        self, ctx: Circumstances,
        tz: RetainsError[Timezone, None],
        latitude: RetainsError[float, None],
        longitude: RetainsError[float, None],
        *, location: RetainsError[str, None],
    ):
        values, errors = RetainsError.unpack(
            tz=tz, latitude=latitude,
            longitude=longitude, location=location,
        )
        if not errors and not values:
            profile: User = await User.aget(ctx.author.id)
            if profile.timezone:
                body = code(profile.timezone)
            else:
                body = 'No timezone preference set.'
            return await ctx.reply(embed=Embed2(
                title='Timezone',
                description=body,
            ).personalized(ctx.author))
        tz = values['tz']
        if tz is not None:
            return await ctx.send(tz)
        lat, long = values['latitude'], values['longitude']
        if lat is not None and long is not None:
            return await ctx.send((lat, long))
        elif lat is not None and long is None:
            return await ctx.send('Missing longitude')
        elif long is not None and lat is None:
            return await ctx.send('Missing latitude')
        query = values['location']
        return await ctx.invoke_with_restrictions(self._get_location, query=query)

    @instruction('!tzlocation', unreachable=True)
    @cooldown(2, 10, BucketType.guild)
    async def _get_location(self, ctx: Circumstances, *, query='test'):
        return await ctx.send(query)
