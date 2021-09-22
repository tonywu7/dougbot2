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

import logging

from django.apps import AppConfig, apps
from django.conf import settings
from django.core.checks import CheckMessage, Error, register
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.signals import connection_created

from .config import AnnotatedPattern, CommandAppConfig


class DiscordBotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ts2.discord'
    default = True

    ext_map: dict[str, CommandAppConfig] = {}
    url_map: dict[str, list[AnnotatedPattern]] = {}

    def sqlite_pragma(self, *, sender, connection: BaseDatabaseWrapper, **kwargs):
        """Enable foreign keys and WAL-mode."""
        if connection.vendor == 'sqlite':
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA foreign_keys=ON;')
                cursor.execute('PRAGMA journal_mode=WAL;')

    def ready(self) -> None:
        """Find installed cogs and start Discord listener."""
        connection_created.connect(self.sqlite_pragma)
        for k, v in apps.app_configs.items():
            if isinstance(v, CommandAppConfig):
                self.ext_map[k] = v
                self.url_map[k] = v.public_views()

        if no_credentials():
            logging.getLogger('discord.config').warning('Discord credentials are missing. Will not connect to Discord.')
            return

        if getattr(settings, 'DISCORD_EAGER_CONNECT', False):
            from .updater import get_updater
            get_updater()

    @property
    def extensions(self) -> dict[str, CommandAppConfig]:
        """Return a mapping of installed cogs."""
        return {**self.ext_map}


@register('discord')
def check_discord_credentials(app_configs: list[AppConfig], **kwargs) -> list[CheckMessage]:
    """Check if Discord client id, secret, or bot token is missing."""
    if no_credentials():
        return [Error('Discord credentials are missing.',
                      hint='Run the init command to supply them.',
                      id='discord.E010')]
    return []


def no_credentials():
    """Return True if any required Discord client credentials is not provided in settings."""
    return (not settings.DISCORD_CLIENT_ID
            or not settings.DISCORD_CLIENT_SECRET
            or not settings.DISCORD_BOT_TOKEN)


def server_allowed(server_id: int):
    """Check if this guild is whitelisted for the program.

    The bot will only respond to events from whitelisted guilds, and
    only whitelisted ones appear on the web console.

    Whitelist is provided through `ALLOWED_GUILDS` in Django settings
    as a list of guild IDs. If no ID is provided (default), all guilds
    are allowed.
    """
    allowed = settings.ALLOWED_GUILDS
    return not allowed or server_id in allowed


def get_app() -> DiscordBotConfig:
    """Access the Django config for the discord app."""
    return apps.get_app_config('discord')


def get_constant(k: str, default=None):
    """Retrieve a value from the `INSTANCE_CONSTANTS` mapping in settings.

    Used for defining miscellaneous values such as bot colors.
    """
    return settings.INSTANCE_CONSTANTS.get(k.upper(), default)


def get_extensions() -> list[CommandAppConfig]:
    """Return app configs for the list of installed cogs."""
    return [app for app in get_app().ext_map.values() if not app.hidden]
