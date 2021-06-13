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

import sys
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import autoreload

from ...bot import BotRunner, Telescope


class Command(BaseCommand):
    help = 'Run the Discord bot'

    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            '--noreload', action='store_false', dest='use_reloader',
            help='Tells Django to not use the auto-reloader.',
        )

    def handle(self, *args, **options):
        self.run(**options)

    def run(self, *, use_reloader: bool = True, **options):
        if use_reloader:
            autoreload.run_with_reloader(self.run_client, **options)
        else:
            self.run_client(**options)

    def run_client(self, **options):
        # If an exception was silenced in ManagementUtility.execute in order
        # to be raised in the child process, raise it now.
        autoreload.raise_last_exception()

        quit_command = 'CTRL-BREAK' if sys.platform == 'win32' else 'CONTROL-C'

        self.stdout.write('Performing system checks...\n\n')
        self.check(display_num_errors=True)
        # Need to check migrations here, so can't use the
        # requires_migrations_check attribute.
        self.check_migrations()

        now = datetime.now().strftime('%B %d, %Y - %X')
        self.stdout.write(now)
        self.stdout.write((
            'Django version %(version)s, using settings %(settings)r\n'
            'Starting Discord bot client\n'
            'Quit the client with %(quit_command)s.'
        ) % {
            'version': self.get_version(),
            'settings': settings.SETTINGS_MODULE,
            'quit_command': quit_command,
        })

        try:
            runner = BotRunner(Telescope, {})
            runner.run()
        except KeyboardInterrupt:
            return
