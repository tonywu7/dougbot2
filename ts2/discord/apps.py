# apps.py
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

from __future__ import annotations

import logging

from cacheops import invalidate_model
from django.apps import AppConfig, apps
from django.conf import settings
from django.core.checks import CheckMessage, Error, Warning, register
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.signals import connection_created
from redis.exceptions import ConnectionError

from ts2.web.config import AnnotatedPattern, CommandAppConfig

from .runner import BotRunner


class DiscordBotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ts2.discord'

    ext_map: dict[str, CommandAppConfig] = {}
    url_map: dict[str, list[AnnotatedPattern]] = {}

    bot_thread: BotRunner

    def sqlite_pragma(self, *, sender, connection: BaseDatabaseWrapper, **kwargs):
        if connection.vendor == 'sqlite':
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA foreign_keys=ON;')
                cursor.execute('PRAGMA journal_mode=WAL;')

    def ready(self) -> None:
        from .bot import Robot

        connection_created.connect(self.sqlite_pragma)
        for k, v in apps.app_configs.items():
            if isinstance(v, CommandAppConfig):
                self.ext_map[k] = v
                self.url_map[k] = v.public_views()

        if (not settings.DISCORD_CLIENT_ID
                or not settings.DISCORD_CLIENT_SECRET
                or not settings.DISCORD_BOT_TOKEN):
            logging.getLogger('discord.config').warning('Discord credentials are missing. Will not connect to Discord.')
            return

        self.bot_thread = BotRunner(Robot, {}, run_forever=False, standby=True, daemon=True)
        self.bot_thread.start()

    @classmethod
    def get(cls) -> DiscordBotConfig:
        return apps.get_app_config('discord')

    @property
    def extensions(self) -> dict[str, CommandAppConfig]:
        return {**self.ext_map}


@register('discord')
def check_discord_credentials(app_configs: list[AppConfig], **kwargs) -> list[CheckMessage]:
    if (not settings.DISCORD_CLIENT_ID
            or not settings.DISCORD_CLIENT_SECRET
            or not settings.DISCORD_BOT_TOKEN):

        return [Error('Discord credentials are missing.',
                      hint='Run the init command to supply them.',
                      id='discord.E010')]
    return []


@register('discord')
def check_command_paths(app_configs: list[AppConfig], **kwargs) -> list[CheckMessage]:
    from .bot import Robot
    from .models import BotCommand
    from .runner import BotRunner

    try:
        invalidate_model(BotCommand)
    except ConnectionError:
        pass

    errors = []

    with BotRunner.instanstiate(Robot, {}) as bot:

        bot: Robot
        cmds = {identifier for identifier, cmd in bot.iter_commands()}

        try:
            registered = {v['identifier'] for v in BotCommand.objects.values('identifier')}
        except Exception as e:
            return [Warning(
                ('Cannot fetch command registry from the database, '
                 f'check cannot continue. Reason: {e}'),
                id='discord.E100',
            )]

        missing = cmds - registered
        deleted = registered - cmds

        if missing:
            errors.append(Error(
                ('The following commands are registered in the bot but '
                 f'not in the database: {", ".join(missing)}'),
                hint='Run the synccmds command to synchronize.',
                id='discord.E001',
            ))
        if deleted:
            errors.append(Error(
                ('The following commands are found in the database but '
                 f'are no longer available in the bot: {", ".join(deleted)}'),
                hint='Run the synccmds command to synchronize.',
                id='discord.E002',
            ))

    return errors