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
from typing import Optional

from django.apps import AppConfig, apps
from django.conf import settings
from django.core.checks import CheckMessage, Error, register
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.signals import connection_created
from django.http import HttpRequest

from .config import AnnotatedPattern, CommandAppConfig
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


def get_commands(req: HttpRequest) -> Optional[list[str]]:
    superuser = req.user.is_superuser
    instance = DiscordBotConfig.get().bot_thread.get_client()
    if not instance:
        return None
    return [*sorted(
        c.qualified_name for c
        in instance.walk_commands()
        if not instance.is_hidden(c) or superuser
    )]


def server_allowed(server_id: int):
    allowed = settings.ALLOWED_GUILDS
    return not allowed or server_id in allowed


def get_constant(k: str, default=None):
    return settings.INSTANCE_CONSTANTS.get(k.upper(), default)
