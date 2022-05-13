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

from django.apps import AppConfig
from django.core.checks import CheckMessage, Error, register
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.signals import connection_created

from .defaults import get_defaults


class DiscordBotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dougbot2"
    default = True

    def sqlite_pragma(self, *, sender, connection: BaseDatabaseWrapper, **kwargs):
        """Enable foreign keys and WAL-mode."""
        if connection.vendor == "sqlite":
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA foreign_keys=ON;")
                cursor.execute("PRAGMA journal_mode=WAL;")

    def ready(self) -> None:
        """Find installed cogs and start Discord listener."""
        connection_created.connect(self.sqlite_pragma)
        if not credentials_supplied():
            logging.getLogger("discord.config").warning(
                "Discord credentials are missing. Will not connect to Discord."
            )


@register("discord")
def check_discord_credentials(
    app_configs: list[AppConfig], **kwargs
) -> list[CheckMessage]:
    """Check if Discord client id, secret, or bot token is missing."""
    if not credentials_supplied():
        return [
            Error(
                "Discord credentials are missing.",
                hint="Run the init command to supply them.",
                id="discord.E010",
            )
        ]
    return []


def credentials_supplied() -> bool:
    try:
        defaults = get_defaults()
    except RuntimeError:
        return False
    auth = defaults.auth
    return bool(auth.bot_token) and bool(auth.client_id) and bool(auth.client_secret)
