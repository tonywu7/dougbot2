# startcog.py
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
import os
from pathlib import Path

from django.core.management.commands.startapp import Command as StartAppCommand


class Command(StartAppCommand):
    help = (
        'Given a name, creates an app directory structure for a Django app + '
        'Discord.py cog in the contrib directory.'
    )
    missing_args_message = 'You must provide an application name.'

    def add_arguments(self, parser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            '--title', action='store', dest='cog_name', default=None,
            help='Qualified name for the new Cog.',
        )
        parser.add_argument(
            '--desc', action='store', dest='cog_description', default='',
            help='Description of the new Cog.',
        )
        parser.add_argument(
            '--order', action='store', type=int, dest='cog_sort_order',
            default=50, help='Sort order of the new Cog to be used in the help command.',
        )

    def handle(self, **options):
        options['template'] = str((Path(__file__).with_name('templates') / 'app.tar.gz').resolve(strict=True))
        options['qual_name'] = qual_name = options['name']
        options['name'] = qual_name.split('.')[-1]
        qual_name: str
        target = Path('.') / qual_name.replace('.', '/')
        if target.parent != Path('.'):
            options['directory'] = str(target.resolve())
            os.makedirs(target, exist_ok=False)
        super().handle(**options)
        logging.getLogger(__name__).info('\nRemember to add the app to INSTALLED_APPS.')
