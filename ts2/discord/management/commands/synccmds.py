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

from cacheops import invalidate_model
from django.core.checks import Tags
from django.core.management.base import BaseCommand
from django.db import Error, transaction
from redis.exceptions import ConnectionError

from ts2.utils.logger import colored as _
from ts2.utils.repl import Form, Question

log = logging.getLogger('manage.syncccommands')


class Command(BaseCommand):
    help = ('Synchronize bot commands defined in the program '
            'with the Django database')

    requires_system_checks = [Tags.models, Tags.database]

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '--dry-run', action='store_true', dest='dry_run',
            help='Do not write changes to the database.',
        )

    def handle(self, *args, dry_run, **options):
        self.sync_commands(dry_run)

    @classmethod
    def insert_cmds(cls, cmds):
        from ...models import BotCommand
        if not cmds:
            return
        BotCommand.objects.bulk_create([
            BotCommand(identifier=name) for name in cmds
        ])
        log.info('The following commands are synchronized to the database:')
        log.info(_(', '.join(cmds), 'cyan', attrs=['bold']))

    @classmethod
    def remove_cmds(cls, cmds):
        from ...models import BotCommand
        if not cmds:
            return
        BotCommand.objects.filter(identifier__in=cmds).delete()
        log.info('The following commands are deleted from the database:')
        log.info(_(', '.join(cmds), 'red', attrs=['bold']))

    @classmethod
    def update_cmds(cls, cmds: dict[str, str]):
        from ...models import BotCommand
        if not cmds:
            return
        commands: dict[str, BotCommand] = {cmd.identifier: cmd for cmd in BotCommand.objects.filter(identifier__in=cmds)}
        for k, v in commands.items():
            v.identifier = cmds[k]
            v.save()
            log.info(_(f'Updated {k} -> {cmds[k]}', 'yellow', attrs=['bold']))

    @classmethod
    def sync_commands(cls, dry_run):
        from ...bot import Robot
        from ...models import BotCommand
        from ...runner import BotRunner

        try:
            invalidate_model(BotCommand)
        except ConnectionError:
            pass

        with BotRunner.instanstiate(Robot, {}) as bot:
            bot: Robot
            designated = {cmd.qualified_name for cmd in bot.walk_commands()}
            registered = {v['identifier'] for v in BotCommand.objects.values('identifier')}

        missing = designated - registered
        deleted = registered - designated

        try:
            with transaction.atomic():

                if not missing and not deleted:
                    log.info(_('All commands synchronized.', 'green', attrs=['bold']))
                    return

                elif not deleted:
                    cls.insert_cmds(missing)

                elif not missing:
                    cls.remove_cmds(deleted)

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
                        log.warning('Form cancelled. Operation aborted.')
                        return

                    selected = form.formdata_filled
                    if len(set(selected.values())) != len(selected.values()):
                        log.error('Duplicate entries found. Operation aborted.')
                        return

                    to_insert = missing - set(selected.values())
                    to_delete = form.formdata_missing.keys()
                    to_update = selected

                    cls.remove_cmds(to_delete)
                    cls.update_cmds(to_update)
                    cls.insert_cmds(to_insert)

                if dry_run:
                    raise NoCommit()

        except NoCommit:
            pass


class CommandForm(Form):
    def __init__(self, questions: list[Question], candidates: list[str]):
        super().__init__(questions)
        self.candidates = candidates

    def completenames(self, text, line, begidx, endidx) -> list[str]:
        return [c for c in self.candidates if c[begidx:endidx] == text]


class NoCommit(Error):
    pass
