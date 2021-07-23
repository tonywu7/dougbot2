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

N_WINTER = datetime(2021, 1, 1)
N_SUMMER = datetime(2021, 6, 1)


class Zone(TypedDict):
    iana: str
    tzname: str
    canonical: float
    summer: float


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
        zones: dict[str, Zone] = {}
        for tzname in pytz.common_timezones:
            tz = pytz.timezone(tzname)
            zone: Zone = {'iana': tzname}
            offset_1 = tz.utcoffset(N_WINTER).total_seconds() / 3600
            offset_2 = tz.utcoffset(N_SUMMER).total_seconds() / 3600
            northern = tz.dst(N_WINTER).total_seconds() == 0
            if northern:
                zone['canonical'] = offset_1
                zone['summer'] = offset_2
                zone['tzname'] = tz.tzname(N_WINTER)
            else:
                zone['canonical'] = offset_2
                zone['summer'] = offset_1
                zone['tzname'] = tz.tzname(N_SUMMER)
            zones[tzname] = zone
        with open(dest, 'w+') as f:
            simplejson.dump(zones, f)
