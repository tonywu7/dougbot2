# init.py
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
from django.core.checks import Tags
from django.core.management.base import BaseCommand

from telescope2.utils.logger import colored as _
from telescope2.utils.repl import Form, Question, missing

log = logging.getLogger('manage.init')


class Command(BaseCommand):
    help = ('Initialize database and app settings.')

    requires_system_checks = [Tags.models, Tags.database]
    requires_migrations_checks = True

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '--discord-client-id', action='store', dest='client_id',
            help='Client ID of your Discord app.', default=missing,
        )
        parser.add_argument(
            '--discord-client-secret', action='store', dest='secret',
            help='Client secret of your Discord app.', default=missing,
        )
        parser.add_argument(
            '--discord-bot-token', action='store', dest='token',
            help='Login token for the bot.', default=missing,
        )

    def handle(self, *args, client_id=missing, secret=missing, token=missing, **options):
        form = Form([
            Question('client_id', 'Discord app client ID', True, value=client_id),
            Question('secret', 'Discord app client secret', True, value=secret),
            Question('token', 'Discord bot login token', True, value=token),
        ])
        form.cmdloop(intro=('Initializing app credentials.\n'
                            'Please enter/confirm the following values.\n'
                            'Use ^C to go to a previous question.'))

        if not form.filled:
            log.warning('Aborted!')
            return

        template = (Path(__file__).with_name('templates') / 'discord.ini').resolve(True)
        with open(template, 'r') as f:
            tmpl = f.read() % form.formdata_filled

        instance_dir: Path = settings.BASE_DIR
        target = instance_dir / 'discord.ini'
        with open(target, 'w+') as f:
            f.write(tmpl)

        log.info(_(f'Exported credentials to {target.resolve()}', 'green'))
