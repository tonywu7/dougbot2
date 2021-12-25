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

import asyncio
import signal
import sys
import time
from contextlib import suppress
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import autoreload

from ...bot import Robot
from ...runner import BotRunner


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
        if use_reloader and settings.DEBUG:
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

        should_exit = False

        def set_signal_handler(client: Robot):
            loop = client.loop

            def on_exit_set_presence():
                asyncio.run_coroutine_threadsafe(client.set_exit_status(), loop)
                nonlocal should_exit
                should_exit = True

            with suppress(RuntimeError):
                client.loop.add_signal_handler(signal.SIGINT, on_exit_set_presence)
                client.loop.add_signal_handler(signal.SIGTERM, on_exit_set_presence)
                client.log.info('Installed handler for SIGTERM and SIGINT')

        try:
            runner = BotRunner(Robot, {}, daemon=True)
            runner.start()
            with runner.init:
                runner.init.wait_for(runner.initialized)
            set_signal_handler(runner.client)
            while not should_exit:
                time.sleep(5)
        except KeyboardInterrupt:
            print('Exiting ...')
            return
