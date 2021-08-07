from django.utils.functional import classproperty
from django.utils.safestring import mark_safe

from ts2.discord.cog import Gear
from ts2.discord.config import CommandAppConfig


class TickerConfig(CommandAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ts2.discord.contrib.ticker'
    default = True

    title = 'Ticker'
    icon = mark_safe('<i class="bi bi-align-top"></i>')

    @classproperty
    def target(cls) -> Gear:
        from .bot import Ticker
        return Ticker
