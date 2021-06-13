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

from typing import Dict, List

from django.apps import AppConfig, apps
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.signals import connection_created

from telescope2.web.config import CommandAppConfig
from telescope2.web.utils.urls import AnnotatedPattern


class DiscordBotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telescope2.discord'

    ext_map: Dict[str, CommandAppConfig] = {}
    url_map: Dict[str, List[AnnotatedPattern]] = {}

    def sqlite_pragma(self, *, sender, connection: BaseDatabaseWrapper, **kwargs):
        if connection.vendor == 'sqlite':
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA foreign_keys=ON;')
                cursor.execute('PRAGMA journal_mode=WAL;')

    def ready(self) -> None:
        connection_created.connect(self.sqlite_pragma)
        for k, v in apps.app_configs.items():
            if isinstance(v, CommandAppConfig):
                self.ext_map[k] = v
                self.url_map[k] = v.public_views()

    @classmethod
    def get(cls) -> DiscordBotConfig:
        return apps.get_app_config('discord')

    @property
    def extensions(self) -> Dict[str, CommandAppConfig]:
        return {**self.ext_map}
