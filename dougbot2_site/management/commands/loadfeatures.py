# dumpfeatures.py
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

from django.core.management.base import BaseCommand
from django.core.serializers import deserialize

from ...models import Feature


class Command(BaseCommand):
    help = 'Delete all existing features and import from a JSON file.'

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '-i', '--input', action='store', dest='source',
            help='Source file',
        )

    def handle(self, *args, source: str, **options):
        Feature.objects.all().delete()
        with open(source, 'r') as f:
            data = f.read()
        for obj in deserialize('json', data):
            obj.save()
