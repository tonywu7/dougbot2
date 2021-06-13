from django.utils.functional import classproperty
from django.utils.safestring import mark_safe

from telescope2.web.config import CommandAppConfig

from ...extension import Gear


class BotUtilityConfig(CommandAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telescope2.discord.contrib.utility'

    title = 'Utilities'
    icon = mark_safe('<i class="bi bi-tools"></i>')

    @classproperty
    def target(cls) -> Gear:
        from .bot import Utilities
        return Utilities
