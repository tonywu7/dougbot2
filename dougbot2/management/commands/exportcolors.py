# exportcolors.py
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

from discord import Colour
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Export discord.py colors to Sass.'

    requires_migrations_checks = []
    requires_system_checks = []

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '-o', '--output', action='store', dest='output',
            help='Destination file',
        )

    def handle(self, *args, output: str, **options):
        with open(output, 'w+') as f:
            for k, v in Colour.__dict__.items():
                if isinstance(v, classmethod):
                    try:
                        c = v.__get__(None, Colour)()
                        f.write(f'$server-{k.replace("_", "-")}: {c};\n')
                    except Exception:
                        pass
