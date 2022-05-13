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

from dataclasses import dataclass
from textwrap import dedent
from typing import Optional, Union
from zoneinfo import ZoneInfo

import arrow
import emoji
from discord import Member, Role
from geopy import Location
from geopy.exc import GeocoderTimedOut

from dougbot2.blueprints import Surroundings
from dougbot2.discord import Gear, command, topic
from dougbot2.exceptions import NotAcceptable, ServiceUnavailable
from dougbot2.exts import autodoc as doc
from dougbot2.utils import osm
from dougbot2.utils.async_ import (
    async_delete,
    async_first,
    async_get_or_create,
    async_list,
    async_save,
)
from dougbot2.utils.common import (
    Color2,
    Embed2,
    EmbedPagination,
    a,
    can_embed,
    code,
    pointer,
    tag,
    tag_literal,
    verbatim,
)
from dougbot2.utils.converters import Timezone
from dougbot2.utils.datetime import get_tzfinder
from dougbot2.utils.dm import accept_dms

from .models import DateTimeSettings, RoleTimezone


@dataclass
class _TimezoneOrigin:
    timezone: ZoneInfo
    subject: Optional[Union[Member, Role]] = None
    location: Optional[Location] = None


def _get_clock_emoji(time: arrow.Arrow) -> str:
    hours = {
        "12": "twelve",
        "01": "one",
        "02": "two",
        "03": "three",
        "04": "four",
        "05": "five",
        "06": "six",
        "07": "seven",
        "08": "eight",
        "09": "nine",
        "10": "ten",
        "11": "eleven",
    }
    hh = hours[time.format("hh")]
    if time.minute >= 30:
        mm = "-thirty"
    else:
        mm = "_o’clock"
    return emoji.emojize(f":{hh}{mm}:")


class TimeandDate(
    Gear,
    name="Time and date",
    order=10,
    description="Tools for date/time and timezone conversions.",
):
    async def get_user_timezone(self, member: Member):
        settings, created = await DateTimeSettings.get_or_create(member)
        return settings

    async def get_role_timezone(self, role_ids: list[int]) -> Optional[RoleTimezone]:
        q = RoleTimezone.objects.filter(snowflake__in=role_ids).prefetch_related("role")
        role_tz: Optional[RoleTimezone] = await async_first(q)
        return role_tz

    async def get_formatting(self, member: Member) -> str:
        if settings := await DateTimeSettings.first(member):
            return settings.formatting
        return self._get_default_dateformat()

    def format_datetime(self, dt: arrow.Arrow, fmt: str):
        if fmt[:9] == "strftime:":
            return dt.strftime(fmt[9:])
        return dt.format(fmt)

    def get_footer(
        self, origin: Union[DateTimeSettings, RoleTimezone], dt: arrow.Arrow
    ) -> str:
        if isinstance(origin, DateTimeSettings):
            return f'Timezone: {dt.format("ZZZ")}'
        elif isinstance(origin, RoleTimezone):
            return f'Difference from UTC: {dt.format("ZZ")} (using server role)'

    async def reply_404(self, ctx: Surroundings, target: Union[Member, Role]):
        res = (
            Embed2(description=f"No timezone info for {tag(target)}")
            .set_color(Color2.red())
            .set_timestamp(None)
            .set_footer(
                text=f'Set timezone preference with the command "{ctx.prefix}timezone set"'
            )
        )
        await ctx.respond(embed=res).autodelete(20).run()

    async def get_timezone_by_roles(
        self, roles: list[Role]
    ) -> Optional[_TimezoneOrigin]:
        rolemap = {r.id: r for r in roles}
        q = RoleTimezone.objects.filter(snowflake__in=rolemap)
        tz: Optional[RoleTimezone] = await async_first(q)
        if not tz:
            return None
        return _TimezoneOrigin(tz.timezone, rolemap[tz.snowflake])

    async def get_timezone_by_user(self, member: Member) -> Optional[_TimezoneOrigin]:
        settings = await DateTimeSettings.first(member)
        if not settings or not settings.timezone:
            return await self.get_timezone_by_roles([*reversed(member.roles)])
        return _TimezoneOrigin(settings.timezone, member)

    @command("time")
    @doc.description("Get the local time of a server member or a timezone.")
    @doc.argument("subject", "The user/role/timezone whose local time to check.")
    @doc.use_syntax_whitelist
    @doc.invocation((), "Show your local time.")
    @doc.invocation(
        ("subject",),
        (
            "Show the local time of a supported IANA timezone, or a user"
            " if they have their timezone preference set,"
            " or a server role, if it is associated with a timezone."
        ),
    )
    @can_embed
    async def time(
        self,
        ctx: Surroundings,
        *,
        subject: Optional[Union[Timezone, Member, Role, str]],
    ):
        if subject is None:
            subject = ctx.author
        if isinstance(subject, str):
            raise NotAcceptable(f"No time info about {verbatim(subject)}.")

        if isinstance(subject, Timezone):
            info = _TimezoneOrigin(subject.value)
        elif isinstance(subject, Member):
            info = await self.get_timezone_by_user(subject)
        elif isinstance(subject, Role):
            info = await self.get_timezone_by_roles([subject])
        else:
            raise ValueError

        if info is None:
            return await self.reply_404(ctx, subject)

        time = arrow.now(tz=info.timezone)
        formatting = await self.get_formatting(ctx.author)
        formatted = self.format_datetime(time, formatting)

        result = (
            Embed2(title="Local time", description=formatted)
            .set_footer(text=f"Timezone: {info.timezone}")
            .set_timestamp(None)
        )
        if isinstance(info.subject, Role):
            result = result.set_color(info.subject.color).set_footer(
                text=f"Timezone: {info.subject.name}"
            )
        if isinstance(subject, Member):
            result = result.personalized(subject)

        await ctx.respond(embed=result).run()

    @topic("timezone")
    @doc.description("Show your timezone preference (if you had set one).")
    @doc.hidden
    @accept_dms
    @can_embed
    async def timezone(self, ctx: Surroundings, *, extras: str = None):
        if extras:
            return await ctx.call(self.timezone_set, timezone=extras)

        embed = Embed2(title="Timezone").personalized(ctx.author)
        settings = await DateTimeSettings.first(ctx.author)
        if not settings or not settings.timezone:
            embed = embed.set_description("No timezone preference set.").set_footer(
                text=f'Set your timezone using the command "{ctx.prefix}timezone set [location]"'
            )
        else:
            formatting = await self.get_formatting(ctx.author)
            timestr = self.format_datetime(arrow.now(tz=settings.timezone), formatting)
            embed = embed.set_description(code(settings.timezone)).add_field(
                name="Local time", value=timestr
            )
        await ctx.respond(embed=embed).reply().run()

    @timezone.command("delete", aliases=("reset", "remove"))
    @doc.description("Reset your timezone preference.")
    @doc.hidden
    @accept_dms
    async def timezone_reset(self, ctx: Surroundings):
        await self.set_timezone(ctx.author, "")
        return await ctx.respond("Your timezone preference has been reset.").run()

    async def get_timezone_by_tz_code(self, name: str) -> Optional[_TimezoneOrigin]:
        if tz := Timezone.get_timezone_from_name(name):
            return _TimezoneOrigin(tz)

    async def get_timezone_by_coords(self, coords: str) -> Optional[_TimezoneOrigin]:
        try:
            point = osm.parse_point_strict(coords)
        except ValueError:
            return None
        tzname = get_tzfinder().timezone_at(lng=point.longitude, lat=point.latitude)
        return _TimezoneOrigin(ZoneInfo(tzname))

    async def get_timezone_by_location(
        self, ctx: Surroundings, query: str
    ) -> Optional[_TimezoneOrigin]:
        try:
            place = await self.get_location(ctx, query)
        except Exception:
            return None
        if place is None:
            return None
        point = place.point
        tzname = get_tzfinder().timezone_at(lng=point.longitude, lat=point.latitude)
        return _TimezoneOrigin(ZoneInfo(tzname), location=place)

    async def get_location(self, ctx: Surroundings, query: str) -> Location:
        try:
            return await ctx.call(osm.get_location, query=query, addressdetails=True)
        except GeocoderTimedOut:
            raise ServiceUnavailable("Searching on OpenStreetMap took too long.")

    async def set_timezone(self, member: Member, tz: ZoneInfo):
        settings, created = await DateTimeSettings.get_or_create(member)
        settings.timezone = tz
        await async_save(settings)
        return settings

    async def reply_set_timezone(
        self,
        ctx: Surroundings,
        settings: DateTimeSettings,
        location: Optional[Location] = None,
    ):
        now = arrow.now(settings.timezone)
        zonename = now.format("ZZZ") or "(unknown)"
        formatted = f"{self.format_datetime(now, settings.formatting)}"
        res = (
            Embed2(title=f"Timezone set: {zonename}")
            .add_field(name="Local time", value=formatted, inline=True)
            .set_footer(text=f"IANA tz code: {settings.timezone}")
            .set_timestamp(None)
        )
        if location:
            location_str = osm.format_coarse_location(location)
            if location_str:
                res = res.add_field(
                    name="Location", value=location_str, inline=True
                ).set_footer(text=f"{res.footer.text} (via OpenStreetMap/Nominatim)")
        await ctx.respond(embed=res).reply().run()

    @timezone.command("set", aliases=("update",))
    @doc.description("Update your timezone preference.")
    @doc.argument(
        "timezone",
        (
            "The timezone to use. This could be an IANA tz code, "
            "geographical coordinates, or the name of a city/state/country, etc."
        ),
    )
    @doc.example("America/New_York", "Specify your timezone using an IANA tz code.")
    @doc.example(
        ("40 -74", "52.3676° N, 4.9041° E"),
        "... using the geographical coordinates of your location.",
    )
    @doc.example(
        ("Seattle WA", "Straße des 17. Juni", "国会議事堂前駅"),
        "... or search for a place directly.",
    )
    @accept_dms
    @can_embed
    async def timezone_set(self, ctx: Surroundings, *, timezone: str):
        for get_tz in [
            lambda: self.get_timezone_by_tz_code(timezone),
            lambda: self.get_timezone_by_coords(timezone),
            lambda: self.get_timezone_by_location(ctx, timezone),
        ]:
            if (result := await get_tz()) is not None:
                break
        else:
            raise NotAcceptable(f"Couldn't find a timezone using {verbatim(timezone)}.")
        settings = await self.set_timezone(ctx.author, result.timezone)
        await self.reply_set_timezone(ctx, settings, result.location)

    def _get_default_dateformat(self) -> str:
        return DateTimeSettings._meta.get_field("formatting").default

    def _print_date_format(self, formatting: str) -> Embed2:
        formatted = self.format_datetime(arrow.now(), formatting)
        return (
            Embed2(title="Date format")
            .add_field(name="Format", value=verbatim(formatting), inline=False)
            .add_field(name="Example", value=formatted, inline=True)
        )

    @topic("dateformat", aliases=("datefmt",))
    @doc.description(
        "Display your date and time format settings (if you have previously set one)."
    )
    @doc.hidden
    @accept_dms
    @can_embed
    async def date_format(self, ctx: Surroundings, *, extras: str = None):
        if extras:
            return await ctx.call(self.date_format_set, specifier=extras)

        default_format = self._get_default_dateformat()
        settings = await DateTimeSettings.first(ctx.author)
        formatting = settings.formatting if settings else default_format
        res = self._print_date_format(formatting)
        return await ctx.respond(embed=res).deleter().run()

    @date_format.command("help")
    @doc.description("Show help on how to specify a date format.")
    @doc.hidden
    @accept_dms
    @can_embed
    async def date_format_help(self, ctx: Surroundings):
        (
            await ctx.respond(embed=DATEFORMAT_HELP)
            .reply()
            .responder(DATEFORMAT_HELP.with_context(ctx))
            .deleter()
            .run()
        )

    @date_format.command("delete", aliases=("reset", "remove"))
    @doc.description("Reset your date format to the default value.")
    @doc.hidden
    @accept_dms
    @can_embed
    async def date_format_reset(self, ctx: Surroundings):
        await async_delete(
            DateTimeSettings.objects.filter(snowflake__exact=ctx.author.id)
        )
        default_format = self._get_default_dateformat()
        res = (
            self._print_date_format(default_format)
            .set_description("Date/time format reset.")
            .personalized(ctx.author)
        )
        await ctx.respond(embed=res).deleter().run()

    @date_format.command("set", aliases=("update",))
    @doc.description(
        "Configure how dates are formatted for date/time related commands."
    )
    @doc.argument("specifier", "Date and time value specifiers.")
    @doc.discussion(
        "Help",
        f' Use the command {code("dateformat help")} for how to specify a format.',
    )
    @accept_dms
    @can_embed
    async def date_format_set(self, ctx: Surroundings, *, specifier: str):
        format_string = {
            "little endian": "DD/MM/YYYY HH:mm",
            "big endian": "YYYY-MM-DD HH:mm",
            "middle endian": "MM/DD/YYYY h:mm A",
        }.get(specifier.lower(), specifier)
        formatting = format_string
        settings, created = await DateTimeSettings.get_or_create(ctx.author)
        settings.formatting = formatting
        await async_save(settings)
        res = self._print_date_format(formatting).set_description(
            "Date/time format updated:"
        )
        return await ctx.respond(embed=res).deleter().run()

    def _print_role_timezones(
        self, *tzs: RoleTimezone, sort_offset: bool = True
    ) -> list[str]:
        now = arrow.now()
        times = [(arrow.Arrow.fromdatetime(now.astimezone(r.timezone)), r) for r in tzs]
        if sort_offset:
            times = sorted(times, key=lambda t: t[0].naive)
        return [
            (
                f"{_get_clock_emoji(t)}"
                f' {code(t.format("HH:mm"))} {tag_literal("role", tz.snowflake)}'
                f' {tz.timezone} ({t.format("ZZ")})'
            )
            for t, tz in times
        ]

    @topic("roletimezone", aliases=("roletz",))
    @doc.description("Role timezone-related commands.")
    @doc.hidden
    async def roletimezone(self, ctx: Surroundings):
        return await ctx.call(self.roletimezone_list)

    @roletimezone.command("list")
    @doc.description("List all server roles with timezones assigned.")
    @can_embed
    async def roletimezone_list(self, ctx: Surroundings):
        roles: list[RoleTimezone] = await async_list(
            RoleTimezone.objects.filter(snowflake__in=[r.id for r in ctx.guild.roles]),
        )
        printed = self._print_role_timezones(*roles)
        pages = EmbedPagination.from_lines(
            printed, "Role timezones", init=lambda c: c.decorated(ctx.guild)
        )
        await ctx.respond(embed=pages).responder(
            pages.with_context(ctx)
        ).deleter().run()

    @roletimezone.command("assign", aliases=("set", "update"))
    @doc.description("Assign a timezone to a server role.")
    @doc.hidden
    @can_embed
    async def roletimezone_assign(
        self,
        ctx: Surroundings,
        role: Role,
        timezone: Timezone,
    ):
        tz, _created = await async_get_or_create(
            RoleTimezone, {"snowflake": role.id}, snowflake=role.id
        )
        tz.timezone = timezone.value
        await async_save(tz)
        await ctx.respond(
            embed=Embed2(
                title="Timezone updated for role:",
                description=self._print_role_timezones(tz)[0],
            )
        ).autodelete(30).run()

    @roletimezone.command("delete", aliases=("reset", "remove"))
    @doc.description("Disassociate a server role with a timezone.")
    @doc.hidden
    @can_embed
    async def roletimezone_remove(self, ctx: Surroundings, role: Role):
        await async_delete(RoleTimezone.objects.filter(snowflake=role.id))
        await ctx.respond(
            embed=Embed2(description=f"Timezone info for {tag(role)} deleted.")
        ).run()


DATEFORMAT_HELP_FRONT = f"""\
Examples:
{code('dateformat set little endian')} {pointer('E')} 22/06/2021 18:40
{code('dateformat set MMM D Y h:mm A')} {pointer('E')} Jun 22 2021 6:40 PM
Specify one or more tokens listed below (case-sensitive).
"""
DATEFORMAT_HELP_CONTENT = [
    (
        "Preset",
        dedent(
            f"""
     {code('middle endian')}: format like 06/22/2021 6:40 PM
     {code('little endian')}: format like 22/06/2021 18:40
     {code('big endian')}: format like 2021-06-21 18:40
     """
        ),
    ),
    (
        "Common date",
        dedent(
            f"""\
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
    """
        ),
    ),
    (
        "Common time",
        dedent(
            f"""\
    {code('HH')}: 00, 01, 02 ... 23, 24
    {code('h')}: 1, 2, 3 ... 11, 12
    {code('mm')}: 00, 01, 02 ... 58, 59
    {code('ss')}: 00, 01, 02 ... 58, 59
    {code('A')}: AM, PM
    {code('Z')}: -07:00, -06:00 ... +06:00, +07:00
    {code('zz')}: EST CST ... MST PST
    """,
        ),
    ),
    (
        "More",
        dedent(
            f"""
    See {a('Pendulum documentation', 'https://pendulum.eustace.io/docs/#tokens')} \
    for a list of all supported tokens.
    See {a('strftime(3)', 'https://man7.org/linux/man-pages/man3/strftime.3.html')} \
    for a list of alternative {code('printf')}-style tokens.
    """
        ),
    ),
]
DATEFORMAT_HELP = EmbedPagination(
    [
        Embed2(description=DATEFORMAT_HELP_FRONT).add_field(name=k, value=v)
        for k, v in DATEFORMAT_HELP_CONTENT
    ],
    "Date time formatting help",
    False,
)
