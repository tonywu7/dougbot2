# runclient.py
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

from django.conf import settings
from django.core.management.base import BaseCommand

from ts2.utils.serve import run


class Command(BaseCommand):
    help = 'Run a simple static files server using aiohttp'

    def handle(self, *args, **options):
        self.run(**options)

    def run(self, **options):
        run(settings.STATIC_ROOT, settings.STATIC_SERVER_PORT)
