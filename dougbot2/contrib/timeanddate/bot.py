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

from contextlib import suppress
from textwrap import dedent
from typing import Literal, Optional, Union

import arrow
import pytz
from discord import Member, Role
from discord.ext.commands import command
from discord.utils import escape_markdown
from geopy import Location
from geopy.exc import GeocoderTimedOut

from dougbot2.cog import Gear
from dougbot2.context import Circumstances
from dougbot2.exceptions import NotAcceptable, ServiceUnavailable
from dougbot2.exts import autodoc as doc
from dougbot2.utils import osm
from dougbot2.utils.async_ import async_first, async_save
from dougbot2.utils.common import (Color2, Embed2, EmbedPagination, a,
                                   blockquote, can_embed, code, tag, verbatim)
from dougbot2.utils.converters import Constant, Maybe, Timezone
from dougbot2.utils.converters.geography import Latitude, Longitude
from dougbot2.utils.datetime import fuzzy_tz_names, get_tzfinder
from dougbot2.utils.english import address

from .models import DateTimeSettings, RoleTimezone

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


class TimeandDate(
    Gear, name='Time and date', order=10,
    description='Tools for date/time and timezone conversions.',
):
    async def get_user_timezone(self, member: Member):
        settings, created = await DateTimeSettings.get_or_create(member)
        return settings.timezone, settings

    async def get_role_timezone(self, role_ids: list[int]):
        q = RoleTimezone.objects.filter(snowflake__in=role_ids).prefetch_related('role')
        role_tz: Optional[RoleTimezone] = await async_first(q)
        return role_tz and role_tz.timezone, role_tz

    async def get_formatting(self, member: Member) -> str:
        if (settings := await DateTimeSettings.first(member)):
            return settings.formatting
        return DateTimeSettings._meta.get_field('formatting').get_default()

    def format_datetime(self, dt: arrow.Arrow, fmt: str):
        if fmt[:9] == 'strftime:':
            return dt.strftime(fmt[9:])
        return dt.format(fmt)

    def get_footer(self, origin: Union[DateTimeSettings, RoleTimezone],
                   dt: arrow.Arrow) -> str:
        if isinstance(origin, DateTimeSettings):
            return f'Timezone: {dt.format("ZZZ")}'
        elif isinstance(origin, RoleTimezone):
            return f'Difference from UTC: {dt.format("ZZ")} (using server role)'

    async def reply_404(self, ctx: Circumstances, target: Union[Member, Role, None]):
        TIMEZONE_NOT_SET = (
            '%(has_vp)s not set %(PRP_REFL)s a timezone preference'
            '\nnor assigned %(PRP_REFL)s a role timezone in the server.'
        )

        if not target:
            hint = (
                'Set timezone preference with '
                + ctx.format_command('my timezone')
            )
            msg = address(TIMEZONE_NOT_SET, ctx.author, ctx, has='has')
            embed = (Embed2(description=msg.capitalize())
                     .set_footer(text=hint)
                     .set_color(Color2.red())
                     .set_timestamp(None))
            return await ctx.reply(embed=embed, delete_after=20)

        if isinstance(target, Member):
            msg = address(TIMEZONE_NOT_SET, target, ctx, has='has')
            embed = (
                Embed2(description=msg.capitalize())
                .set_color(Color2.red())
                .set_timestamp(None)
            )
            return await ctx.reply(embed=embed, delete_after=20)

        elif isinstance(target, Role):
            msg = f'{tag(target)} has no associated timezone.'
            embed = (Embed2(description=msg)
                     .set_color(Color2.red())
                     .set_timestamp(None))
            return await ctx.reply(embed=embed, delete_after=20)

        else:
            raise NotAcceptable(
                'Cannot find a timezone, user, or server role'
                f' using {code(ctx.raw_input)}',
            )

    @command('time')
    @doc.description('Get local time of a server member or a timezone.')
    @doc.argument('subject', 'The user/role/timezone whose local time to check.')
    @doc.use_syntax_whitelist
    @doc.invocation((), 'Show your local time.')
    @doc.invocation(('subject',), (
        'Show the local time of a supported IANA timezone, or a user'
        ' if they have their timezone preference set,'
        ' or a server role, if it is associated with a timezone.'
    ))
    @Maybe.ensure
    @can_embed
    async def time(
        self, ctx: Circumstances, *,
        subject: Maybe[Union[Timezone, Member, Role], None],
    ):
        """Check user local time."""
        timezone: Optional[pytz.BaseTzInfo] = None
        errors = subject.errors
        target = subject.value

        person: Optional[Member] = None
        role_ids: list[int] = []
        role_tz: Optional[RoleTimezone] = None
        if isinstance(target, pytz.BaseTzInfo):
            timezone = target.value
        elif isinstance(target, Role):
            role_ids = [target.id]
        elif isinstance(target, Member):
            person = target
            role_ids = [r.id for r in person.roles]
        else:
            person = ctx.author
            role_ids = [r.id for r in ctx.author.roles]

        if not timezone and person:
            timezone, origin = await self.get_user_timezone(person)
        if not timezone and role_ids:
            timezone, origin = await self.get_role_timezone(role_ids)
        if not timezone:
            return await self.reply_404(ctx, target)

        time = arrow.now(tz=timezone)

        formatting = await self.get_formatting(person)
        formatted = self.format_datetime(time, formatting)

        result = (
            Embed2(title='Local time', description=formatted)
            .set_footer(text=self.get_footer(timezone, origin))
            .set_timestamp(None)
        )
        if person:
            result = result.personalized(person)
        elif role_tz:
            result = result.set_color(role_tz.role.color)
        await ctx.reply(embed=result)

        if len(errors) == 3:
            error = (Embed2(description='\n'.join([str(e) for e in errors]))
                     .set_color(Color2.red()))
            await ctx.response(ctx, embed=error).autodelete(30).run()

    async def set_timezone(self, member: Member, tz: pytz.BaseTzInfo):
        settings, created = await DateTimeSettings.get_or_create(member)
        settings.timezone = tz
        await async_save(settings)
        return settings

    async def reply_set_timezone(
        self, ctx: Circumstances,
        settings: DateTimeSettings,
        location: Optional[Location] = None,
        *, notify: bool = True,
        msg: str = '',
        delete: bool = False,
    ):
        now = arrow.now(settings.timezone)
        zonename = now.format('ZZZ') or '(unknown)'
        formatted = f'{self.format_datetime(now, settings.formatting)}'
        res = (
            Embed2(title=f'Timezone set: {zonename}')
            .add_field(name='Local time', value=formatted, inline=True)
            .set_footer(text=f'IANA tz code: {settings.timezone}')
            .set_timestamp(None)
        )
        if location:
            location_str = osm.format_coarse_location(location)
            if location_str:
                res = res.add_field(name='Location', value=location_str, inline=True)
        if delete:
            await ctx.message.delete(delay=0.1)
        if notify:
            await ctx.response(ctx, embed=res).pingback().run()
        else:
            await ctx.reply(embed=res)
        if msg:
            await ctx.response(ctx, embed=Embed2(description=msg)).autodelete(60).run()

    async def reply_current_timezone(self, ctx: Circumstances, member: Member):
        settings, created = await DateTimeSettings.get_or_create(member)
        embed = Embed2(title='Timezone').personalized(member)
        if settings.timezone:
            embed = (embed.set_description(code(settings.timezone))
                     .add_field(name='Local time', value=self.format_datetime(arrow.now())))
        else:
            embed = (embed.set_description('No timezone preference set.')
                     .set_footer(text=f'Set timezone with "{self.timezone.name} [location]"'))
        return await ctx.reply(embed=embed)

    def parse_point(self, lat: Optional[float], long: Optional[float], raw_input: str):
        try:
            point = osm.parse_point_strict(raw_input)
        except ValueError:
            if lat is not None and long is not None:
                raise ValueError
            elif lat is not None:
                raise ValueError(
                    f'Successfully parsed latitude {lat:.3f}'
                    ' but longitude not found or cannot be parsed.',
                )
            else:
                raise ValueError(
                    f'Successfully parsed longitude {long:.3f}'
                    ' but latitude not found or cannot be parsed.',
                )
        return point

    async def get_location(self, ctx: Circumstances, query: str) -> Location:
        try:
            return await ctx.call(osm.get_location, query=query, addressdetails=True)
        except GeocoderTimedOut:
            raise ServiceUnavailable('Searching on OpenStreetMap took too long.')

    @command('timezone')
    @doc.description('Configure your timezone.')
    @doc.argument('reset', signature='-reset', node='-reset')
    @doc.argument('tz', 'Timezone to set.')
    @doc.argument('latitude', 'Latitude of the location whose timezone to use.')
    @doc.argument('longitude', 'Longitude of the location whose timezone to use.')
    @doc.argument('location', 'Name of a location to search for.')
    @doc.use_syntax_whitelist
    @doc.invocation((), 'Print your current timezone preference.')
    @doc.invocation(('reset',), 'Remove your timezone preference.')
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
    @can_embed
    @Maybe.ensure
    async def timezone(
        self, ctx: Circumstances,
        reset: Maybe[Constant[Literal['-reset']], None],
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

        if reset.value:
            await self.set_timezone(author, '')
            return await ctx.reply('Your timezone preference has been reset.')

        if not errors and not values:
            return await self.reply_current_timezone(ctx, author)

        tz = values['tz']
        if tz is not None:
            settings = await self.set_timezone(author, tz)
            return await self.reply_set_timezone(ctx, settings, tz, notify=False)

        lat: Optional[float] = values['latitude']
        long: Optional[float] = values['longitude']
        query: Optional[str] = values['location']
        raw_input = Maybe.reconstruct(latitude, longitude, location)

        if query is None and lat is not None and long is not None:
            tzname = get_tzfinder().timezone_at(lng=long, lat=lat)
            tz = pytz.timezone(tzname)
            settings = await self.set_timezone(author, tz)
            return await self.reply_set_timezone(ctx, settings, tz, delete=True)

        problems: list[str] = []

        try:
            point = self.parse_point(lat, long, raw_input)
        except ValueError as e:
            problems.append(str(e))
        else:
            tzname = get_tzfinder().timezone_at(lng=point.longitude, lat=point.latitude)
            tz = pytz.timezone(tzname)
            settings = await self.set_timezone(author, tz)
            return await self.reply_set_timezone(ctx, settings, tz, delete=True)

        async with ctx.typing():
            query = raw_input
            try:
                place = await self.get_location(ctx, query)
            except Exception as e:
                problems.append(str(e))
            else:
                problems = []

        potential_tzs = fuzzy_tz_names(raw_input)
        if potential_tzs:
            names = ', '.join(potential_tzs)
            problems.append((
                f'Assumed {verbatim(query)} is a place, did you mean timezones'
                f'\n{blockquote(names)}\ninstead?'
            ))

        if not place:
            with suppress(Exception):
                await ctx.message.delete()
            msg = f'Failed to find a location on OpenStreetMap using {verbatim(query)}'
            msg = '\n'.join([msg, *problems])
            raise NotAcceptable(msg.strip())

        point = place.point
        tzname = get_tzfinder().timezone_at(lng=point.longitude, lat=point.latitude)
        tz = pytz.timezone(tzname)
        settings = await self.set_timezone(author, tz)
        return await self.reply_set_timezone(ctx, settings, tz, location=place,
                                             msg='\n'.join(problems), delete=True)

    @command('dateformat', aliases=('datefmt',))
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
    @can_embed
    async def date_format(
        self, ctx: Circumstances,
        help: Optional[Constant[Literal['-help']]] = None,
        libc: Optional[Constant[Literal['-libc']]] = None,
        reset: Optional[Constant[Literal['-reset']]] = None,
        *, format_string: Optional[str] = None,
    ):
        if help:
            return (
                await ctx.response(ctx, embed=DATEFORMAT_HELP)
                .reply().responder(DATEFORMAT_HELP.with_context(ctx))
                .deleter().run()
            )

        if reset:
            formatting = DateTimeSettings._meta.get_field('formatting').default
        elif format_string:
            if libc:
                format_string = f'strftime:{format_string}'
            format_string = {
                'little endian': 'DD/MM/YYYY HH:mm',
                'big endian': 'YYYY-MM-DD HH:mm',
                'middle endian': 'MM/DD/YYYY h:mm A',
            }.get(format_string.lower(), format_string)
            formatting = format_string

        settings, created = await DateTimeSettings.get_or_create(ctx.author)
        settings.formatting = formatting
        await async_save(settings)

        formatted = self.format_datetime(arrow.now(), formatting)
        embed = (
            Embed2(title='Date format')
            .add_field(name='Format', value=code(escape_markdown(formatting)), inline=False)
            .add_field(name='Local time', value=formatted, inline=True)
            .personalized(ctx.author)
        )
        return await ctx.send(embed=embed)
