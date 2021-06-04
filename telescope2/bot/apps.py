from django.apps import AppConfig
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.signals import connection_created


class BotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telescope2.bot'

    def sqlite_pragma(self, *, sender, connection: BaseDatabaseWrapper, **kwargs):
        if connection.vendor == 'sqlite':
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA foreign_keys=ON;')
                cursor.execute('PRAGMA journal_mode=WAL;')

    def ready(self) -> None:
        connection_created.connect(self.sqlite_pragma)
