from django.utils.functional import classproperty
from django.utils.safestring import mark_safe

from ts2.discord.cog import Gear
from ts2.discord.config import CommandAppConfig


class BotUtilityConfig(CommandAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ts2.discord.contrib.utility'

    title = 'Utilities'
    icon = mark_safe('<i class="bi bi-tools"></i>')

    @classproperty
    def target(cls) -> Gear:
        from .bot import Utilities
        return Utilities
