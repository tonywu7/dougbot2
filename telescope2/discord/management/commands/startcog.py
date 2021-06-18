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

    def handle(self, **options):
        app_name = options['name']
        options['template'] = str(Path(__file__).with_name('template.tar.gz').resolve(strict=True))
        options['directory'] = target = str(Path(__file__).parent.parent.with_name('contrib') / app_name)
        os.makedirs(target, exist_ok=False)
        super().handle(**options)
        logging.getLogger(__name__).info('\nRemember to add the app to INSTALLED_APPS.')
