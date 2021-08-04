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

from textwrap import dedent
from typing import Literal, Optional

import pytz
from discord import Member
from discord.ext.commands import command, group
from discord.utils import escape_markdown
from geopy import Location, Point
from geopy.exc import GeocoderTimedOut

from ...cog import Gear
from ...context import Circumstances
from ...ext import autodoc as doc
from ...ext.autodoc import NotAcceptable
from ...ext.dm import accepts_dms
from ...ext.types.functional import Maybe
from ...ext.types.patterns import Constant
from ...utils.duckcord.embeds import Embed2
from ...utils.markdown import a, arrow, code, verbatim
from ...utils.pagination import EmbedPagination
from ..services import ServiceUnavailable
from ..services.datetime import Timezone, get_tzfinder
from ..services.osm import (Latitude, Longitude, format_coarse_location,
                            get_location)
from .models import User


async def set_tz(member: Member, tz: pytz.BaseTzInfo):
    profile: User = await User.async_get(member)
    await profile.save_timezone(tz)
    return profile


def format_tz_set(user: User, location: Optional[Location] = None) -> Embed2:
    dt = user.gettime()
    zonename = user.timezone.tzname(dt.replace(tzinfo=None)) or '(unknown)'
    dtstr = f'{user.format_datetime(dt)}'
    embed = (
        Embed2(title=f'Timezone set: {zonename}')
        .add_field(name='Local time', value=dtstr, inline=True)
        .set_footer(text=f'IANA tz code: {user.timezone}')
        .set_timestamp(None)
    )
    if location:
        location_str = format_coarse_location(location)
        if location_str:
            embed = embed.add_field(name='Location', value=location_str, inline=True)
    return embed


DATEFORMAT_HELP_FRONT = f"""\
Specify one or more tokens listed below (case-sensitive).
Examples:
{code('my dateformat little endian')} {arrow('E')} 22/06/2021 18:40
{code('my dateformat MMM D Y h:mm A')} {arrow('E')} Jun 22 2021 6:40 PM
"""
DATEFORMAT_HELP_CONTENT = [
    ('Preset', dedent(f"""
     {code('middle endian')}: format like 06/22/2021 6:40 PM
     {code('little endian')}: format like 22/06/2021 18:40
     {code('big endian')}: format like 2021-06-21 18:40
     """)),
    ('Common date', dedent(f"""\
    {code('Y')}, {code('YYYY')}: 2021, 2022, 2023, ...
    {code('YY')}: 21, 22, 23, ...
    {code('MMMM')}: January, Feburary, ...
    {code('MMM')}: Jan, Feb, Mar ...
    {code('MM')}: 01, 02, 03 ... 11, 12
    {code('M')}: 1, 2, 3 ... 11, 12
    {code('DD')}: 01, 02, 03 ... 30, 31
    {code('D')}: 1, 2, 3 ... 30, 31
    {code('Do')}: 1st, 2nd, 3rd ... 30th, 31st
    {code('dddd')}: Monday, Tuesday, Wednesday ...
    {code('ddd')}: Mon, Tue, Wed ...
    """)),
    ('Common time', dedent(f"""\
    {code('HH')}: 00, 01, 02 ... 23, 24
    {code('h')}: 1, 2, 3 ... 11, 12
    {code('mm')}: 00, 01, 02 ... 58, 59
    {code('ss')}: 00, 01, 02 ... 58, 59
    {code('A')}: AM, PM
    {code('Z')}: -07:00, -06:00 ... +06:00, +07:00
    {code('zz')}: EST CST ... MST PST
    """)),
    ('More', dedent(f"""
    See {a('Pendulum documentation', 'https://pendulum.eustace.io/docs/#tokens')} \
    for a list of all supported tokens.
    See {a('strftime(3)', 'https://man7.org/linux/man-pages/man3/strftime.3.html')} \
    for a list of alternative {code('printf')}-style tokens.
    """)),
]
DATEFORMAT_HELP = EmbedPagination([
    Embed2(description=DATEFORMAT_HELP_FRONT)
    .add_field(name=k, value=v)
    for k, v in DATEFORMAT_HELP_CONTENT
], 'Date time formatting help', False)


class Personalize(
    Gear, name='Settings', order=30,
    description='Commands for personalization',
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @command('gdpr', aliases=('export',))
    @doc.description('Get a copy of everything the bot knows about you via DM.')
    @doc.hidden
    async def gdpr(self, ctx: Circumstances):
        pass

    @command('me', invoke_without_command=True)
    @accepts_dms
    @doc.description('Print your settings within the bot.')
    async def me(self, ctx: Circumstances):
        profile: User = await User.async_get(ctx.author)

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

    @group('my', aliases=('conf',))
    @accepts_dms
    @doc.description('Configure various preferences.')
    async def conf(self, ctx: Circumstances):
        pass

    @conf.command('timezone', aliases=('tz',))
    @doc.description('Configure your timezone.')
    @doc.argument('delete', signature='-delete', node='-delete')
    @doc.argument('tz', 'Timezone to set.')
    @doc.argument('latitude', 'Latitude of the location whose timezone to use.')
    @doc.argument('longitude', 'Longitude of the location whose timezone to use.')
    @doc.argument('location', 'Name of a location to search for.')
    @doc.use_syntax_whitelist
    @doc.invocation((), 'Print your current timezone preference.')
    @doc.invocation(('delete',), 'Remove your timezone preference.')
    @doc.invocation(('tz',), 'Set your timezone using an IANA timezone code.')
    @doc.invocation(('latitude', 'longitude'), 'Set your timezone using coordinates (latitude first).')
    @doc.invocation(('location',), 'Set your timezone by searching for a location.')
    @doc.discussion('Privacy', (
        'When setting timezones using lat/long or a location query,'
        ' your message will be immediately deleted.\n'
        'The bot does not keep your location info.'
    ))
    @doc.example('America/New_York', 'Directly using an IANA timezone.')
    @doc.example(('40 -74', '52.3676° N, 4.9041° E'), 'Using the geographical coordinates of your location.')
    @doc.example(('Seattle WA', 'Straße des 17. Juni', '国会議事堂前駅'), 'Or search for a place directly.')
    @Maybe.ensure
    async def timezone(
        self, ctx: Circumstances,
        delete: Maybe[Constant[Literal['-delete']], None],
        tz: Maybe[Timezone, None],
        latitude: Maybe[Latitude, None],
        longitude: Maybe[Longitude, None],
        *, location: Maybe[str, None],
    ):
        author = ctx.author
        values, errors = Maybe.unpack(
            tz=tz, latitude=latitude,
            longitude=longitude, location=location,
        )

        async def commit_tz(tz: pytz.BaseTzInfo, location: Optional[Location] = None,
                            notify: bool = True, delete: bool = False):
            profile = await set_tz(author, tz)
            res = format_tz_set(profile, location).personalized(author)
            if notify:
                await ctx.response(ctx, embed=res).pingback().run()
            else:
                await ctx.reply(embed=res)
            if delete:
                await ctx.message.delete(delay=0.1)

        if delete.value:
            await set_tz(author, '')
            return await ctx.reply('Your timezone preference has been reset.')

        if not errors and not values:
            profile: User = await User.async_get(author)
            embed = Embed2(title='Timezone').personalized(author)
            if profile.timezone:
                embed = (embed.set_description(code(profile.timezone))
                         .add_field(name='Local time', value=profile.format_datetime()))
            else:
                embed = embed.set_description('No timezone preference set.')
            return await ctx.reply(embed=embed)

        tz = values['tz']
        if tz is not None:
            return await commit_tz(tz, notify=False)

        query: Optional[str] = values['location']
        lat: Optional[float] = values['latitude']
        long: Optional[float] = values['longitude']
        raw_input = ctx.raw_input

        tzfinder = get_tzfinder()
        if query is None:
            if lat is not None and long is not None:
                tzname = tzfinder.timezone_at(lng=long, lat=lat)
                tz = pytz.timezone(tzname)
                return await commit_tz(tz, delete=True)

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
            tzname = tzfinder.timezone_at(lng=point.longitude, lat=point.latitude)
            tz = pytz.timezone(tzname)
            return await commit_tz(tz, delete=True)

        query = raw_input
        async with ctx.typing():
            try:
                place: list[Location] = await ctx.call(
                    get_location, query=raw_input,
                    addressdetails=True,
                )
            except GeocoderTimedOut:
                await ctx.message.delete(delay=0.1)
                raise ServiceUnavailable('Searching on OpenStreetMap took too long.')

        if not place:
            await ctx.message.delete(delay=0.1)
            msg = f'Failed to find a location on OpenStreetMap using {verbatim(query)}'
            if bad_coord:
                msg = f'{msg}\nAdditionally, {bad_coord}'
            raise NotAcceptable(msg)

        point = place.point
        tzname = tzfinder.timezone_at(lng=point.longitude, lat=point.latitude)
        tz = pytz.timezone(tzname)
        return await commit_tz(tz, location=place, delete=True)

    @conf.command('dateformat', aliases=('datefmt',))
    @doc.description('Configure how dates are formatted for date/time related commands.')
    @doc.argument('help', signature='-help', node='-help')
    @doc.argument('reset', signature='-reset', node='-reset')
    @doc.argument('libc', f'Use {code("strftime(3)")} format specifiers.',
                  signature='-libc', node='-libc')
    @doc.argument('format_string', 'Date and time value specifiers.')
    @doc.use_syntax_whitelist
    @doc.invocation((), 'Display your current set format.')
    @doc.invocation(('help',), 'Show help on how to specify a format.')
    @doc.invocation(('reset',), 'Reset your date format to the default value.')
    @doc.invocation(('format_string',), 'Set your datetime format.')
    async def date_format(
        self, ctx: Circumstances,
        help: Optional[Constant[Literal['-help']]] = None,
        libc: Optional[Constant[Literal['-libc']]] = None,
        reset: Optional[Constant[Literal['-reset']]] = None,
        *, format_string: Optional[str] = None,
    ):
        if help:
            msg, paginator = await DATEFORMAT_HELP.reply(ctx, 720)
            return await ctx.response(ctx).deleter().responder(lambda msg: paginator).run(msg)

        profile: User = await User.async_get(ctx.author)
        if reset:
            profile.datetimefmt = User._meta.get_field('datetimefmt').default
            await profile.async_save()
        elif format_string:
            if libc:
                format_string = f'strftime:{format_string}'
            format_string = {
                'little endian': 'DD/MM/YYYY HH:mm',
                'big endian': 'YYYY-MM-DD HH:mm',
                'middle endian': 'MM/DD/YYYY h:mm A',
            }.get(format_string.lower(), format_string)
            profile.datetimefmt = format_string
            await profile.async_save()

        fmt = code(escape_markdown(profile.datetimefmt))
        embed = (
            format_tz_set(profile)
            .set_title('Date format')
            .insert_field_at(0, name='Format', value=fmt, inline=True)
            .personalized(ctx.author)
        )
        return await ctx.send(embed=embed)
