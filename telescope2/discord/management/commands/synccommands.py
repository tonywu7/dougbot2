# synccommands.py
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
from typing import Dict, List

from django.core.checks import Tags
from django.core.management.base import BaseCommand
from django.db import Error, transaction

from telescope2.utils.logger import colored as _
from telescope2.utils.repl import Form, Question


class Command(BaseCommand):
    help = ('Synchronize bot commands defined in the program '
            'with the Django database')

    requires_system_checks = [Tags.models, Tags.database]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger('manage.syncccommands')

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '--dry-run', action='store_true', dest='dry_run',
            help='Do not write changes to the database.',
        )

    def insert_cmds(self, cmds):
        from ...models import BotCommand
        BotCommand.objects.bulk_create([
            BotCommand(identifier=name) for name in cmds
        ])
        self.log.info('The following commands are synchronized to the database:')
        self.log.info(_(' '.join(cmds), 'cyan', attrs=['bold']))

    def remove_cmds(self, cmds):
        from ...models import BotCommand
        BotCommand.objects.filter(identifier__in=cmds).delete()
        self.log.info('The following commands are deleted from the database:')
        self.log.info(_(' '.join(cmds), 'red', attrs=['bold']))

    def update_cmds(self, cmds: Dict[str, str]):
        from ...models import BotCommand
        commands: Dict[str, BotCommand] = {cmd.identifier: cmd for cmd in BotCommand.objects.filter(identifier__in=cmds)}
        for k, v in commands.items():
            v.identifier = cmds[k]
            v.save()
            self.log.info(_(f'Updated {k} -> {cmds[k]}', 'yellow', attrs=['bold']))

    def handle(self, *args, dry_run, **options):
        from ...bot import BotRunner, Telescope
        from ...models import BotCommand

        with BotRunner.instanstiate(Telescope, {}) as bot:
            bot: Telescope
            designated = {identifier for identifier, cmd in bot.iter_commands()}
            registered = {v['identifier'] for v in BotCommand.objects.values('identifier')}

        missing = designated - registered
        deleted = registered - designated

        try:
            with transaction.atomic():

                if not missing and not deleted:
                    self.log.info(_('All commands synchronized.', 'green', attrs=['bold']))
                    return

                elif not deleted:
                    self.insert_cmds(missing)

                elif not missing:
                    self.remove_cmds(deleted)

                else:
                    form = CommandForm([
                        Question(key=identifier, prompt=identifier, required=False)
                        for identifier in deleted
                    ], missing)
                    form.cmdloop(intro=(
                        'System check identified both new and deleted commands.\n'
                        'Please map the following commands from the database to a new command.\n'
                        'Leave the field empty if the command is to be deleted.\n'
                        'Use Tab to see a list of candidate commands.'
                    ))
                    if not form.filled:
                        self.log.warning('Form cancelled. Operation aborted.')
                        return

                    selected = form.formdata_filled
                    if len(set(selected.values())) != len(selected.values()):
                        self.log.error('Duplicate entries found. Operation aborted.')
                        return

                    to_insert = missing - set(selected.values())
                    to_delete = form.formdata_missing.keys()
                    to_update = selected

                    self.remove_cmds(to_delete)
                    self.update_cmds(to_update)
                    self.insert_cmds(to_insert)

                if dry_run:
                    raise NoCommit()

        except NoCommit:
            pass


class CommandForm(Form):
    def __init__(self, questions: List[Question], candidates: List[str]):
        super().__init__(questions)
        self.candidates = candidates

    def completenames(self, text, line, begidx, endidx) -> List[str]:
        return [c for c in self.candidates if c[begidx:endidx] == text]


class NoCommit(Error):
    pass
