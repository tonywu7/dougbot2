from typing import Dict, List

from django.apps import AppConfig, apps
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.signals import connection_created

from telescope2.web.utils.config import CommandAppConfig
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
