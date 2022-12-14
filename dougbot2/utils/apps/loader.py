# loader.py
# Copyright (C) 2022  @tonyzbf +https://github.com/tonyzbf/
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

from ...blueprints import MissionControl
from .. import converters
from ..converters import (
    InvalidChoices,
    NumberOutOfBound,
    RegExpMismatch,
    datetime,
    geography,
)
from ..english import NP, coord_conj


def _convert_maybe(t: converters.Maybe):
    return t._converter


def _convert_bounded_number(c: converters.BoundedNumber):
    return NP(
        f"number between {c.lower} and {c.upper}, inclusive",
        concise=f"number between {c.lower} and {c.upper}",
    )


def _convert_choice(c: converters.Choice):
    full_name = "one of the following"
    predicative = coord_conj(*[f'"{w}"' for w in c.choices], conj="or")
    if c.case_sensitive:
        predicative = f"{predicative}, case sensitive"
    return NP(
        full_name,
        concise=c.name,
        predicative=predicative,
        predicative_sep=": ",
        definite=True,
        uncountable=True,
    )


def _convert_constant(c: converters.Constant):
    return NP(
        f'exact text "{c.const}"',
        concise=f'"{c.const}"',
        predicative="without the quotes",
        definite=True,
    )


def _convert_regexp(c: converters.RegExp):
    name = c.name or "pattern"
    predicative = c.description or (f"matching the regular expression {c.pattern}")
    return NP(name, predicative=predicative)


def setup(bot: MissionControl):
    doc = bot.manpage

    doc.register_type(converters.Datetime, NP("date/time"))
    doc.register_type(
        converters.Timedelta,
        NP("duration", predicative="such as `60s`, `1h13m36s`, or `3w6d`"),
    )

    doc.register_type(converters.PermissionName, NP("permission name"))
    doc.register_type(converters.Maybe, _convert_maybe)

    doc.register_type(converters.BoundedNumber, _convert_bounded_number)
    doc.register_type(converters.Choice, _convert_choice)
    doc.register_type(converters.Constant, _convert_constant)
    doc.register_type(
        converters.Lowercase,
        NP("text", predicative="case insensitive", uncountable=True),
    )
    doc.register_type(converters.RegExp, _convert_regexp)

    doc.register_type(converters.JSON, NP("JSON code block"))
    doc.register_type(converters.TOML, NP("TOML code block"))
    doc.register_type(converters.JinjaTemplate, NP("Jinja code block"))
    doc.register_type(converters.Dictionary, NP("TOML or JSON code block"))

    doc.register_type(
        datetime.Timezone,
        NP(
            "IANA tz code",
            predicative=(
                "see [list of timezones](https://en.wikipedia.org/"
                "wiki/List_of_tz_database_time_zones)"
            ),
        ),
    )
    doc.register_type(
        geography.Latitude,
        NP("latitude", predicative="such as `-41.5`, `41.5N`, or `N 39??`"),
    )
    doc.register_type(
        geography.Longitude,
        NP("longitude", predicative="such as `-110`, `30E`, or `E 162??`"),
    )

    err = bot.errorpage
    err.add_error_fluff(
        (
            RegExpMismatch,
            NumberOutOfBound,
            InvalidChoices,
        ),
        "HTTP 400 Bad Request",
        "That ain't it chief.",
        "What?",
    )
