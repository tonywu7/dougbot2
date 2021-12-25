# initserver.py
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

import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from ts2.utils.logger import colored as _
from ts2.utils.repl import Form, Question, missing

log = logging.getLogger('manage.init')


class Command(BaseCommand):
    help = ('Initialize server settings.')

    requires_system_checks = []
    requires_migrations_checks = False

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '--allowed-hosts', action='store', dest='allowed_hosts',
            help='Client ID of your Discord app.', default=missing,
        )

    def handle(self, *args, allowed_hosts=missing, **options):
        logging.disable(logging.ERROR)

        form = Form([
            Question('allowed_hosts', 'ALLOWED_HOSTS', True, value=allowed_hosts),
        ])
        form.cmdloop(intro=('Initializing Django settings\n'
                            'Please enter/confirm the following values.\n'
                            'Use ^C to go to a previous question.'))

        if not form.filled:
            log.warning('Aborted!')
            return

        template = (Path(__file__).with_name('templates') / 'server.ini').resolve(True)
        with open(template, 'r') as f:
            tmpl = f.read() % form.formdata_filled

        instance_dir: Path = settings.INSTANCE_DIR
        target = instance_dir / 'server.ini'
        with open(target, 'w+') as f:
            f.write(tmpl)

        print(_(f'Exported settings to {target.resolve()}', 'green'))
