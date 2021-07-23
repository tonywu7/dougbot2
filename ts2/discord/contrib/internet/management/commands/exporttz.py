# exporttz.py
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

from datetime import datetime
from pathlib import Path
from typing import TypedDict

import pytz
import simplejson
from django.core.management.base import BaseCommand
from PIL import ImageColor

N_WINTER = datetime(datetime.now().year, 1, 1)
N_SUMMER = datetime(datetime.now().year, 6, 1)


class Zone(TypedDict):
    iana: str
    tzname: str
    canonical: float
    summer: float

    mean_offset: float
    offset: str
    content: str
    foreground: str


def rgb2hex(r: int, g: int, b: int):
    return f'#{(r << 16) + (g << 8) + b:06x}'


class Command(BaseCommand):
    help = 'Export all pytz supported timezones to a JSON file.'

    requires_migrations_checks = []
    requires_system_checks = []

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '-o', '--output', action='store', dest='output',
            help='Destination file',
        )

    def handle(self, *args, output: str, **options):
        dest = Path(output).resolve()
        zones: list[Zone] = []
        for tzname in pytz.common_timezones:
            tz = pytz.timezone(tzname)
            zone: Zone = {'iana': tzname}
            offset_1 = tz.utcoffset(N_WINTER).total_seconds() / 3600
            offset_2 = tz.utcoffset(N_SUMMER).total_seconds() / 3600
            northern = tz.dst(N_WINTER).total_seconds() == 0
            if northern:
                canonical = zone['canonical'] = offset_1
                summer = zone['summer'] = offset_2
                zone['tzname'] = tz.tzname(N_WINTER)
            else:
                canonical = zone['canonical'] = offset_2
                summer = zone['summer'] = offset_1
                zone['tzname'] = tz.tzname(N_SUMMER)
            mean_offset = zone['mean_offset'] = (offset_1 + offset_2) / 2
            readable = tzname.replace('/', ' - ').replace('_', ' ')
            if offset_1 == offset_2:
                offset = zone['offset'] = f'{canonical:+g}'
            else:
                offset = zone['offset'] = f'{canonical:+g}/{summer:+g}'
            zone['content'] = f'{offset} : {readable}'
            hue = 15 * ((mean_offset + 12) % 24)
            zone['foreground'] = rgb2hex(*ImageColor.getrgb(f'hsl({hue}, 60%, 75%)'))
            zones.append(zone)
        zones = [*sorted(zones, key=lambda z: (z['mean_offset'], z['canonical'], z['iana']))]
        with open(dest, 'w+') as f:
            simplejson.dump(zones, f)
