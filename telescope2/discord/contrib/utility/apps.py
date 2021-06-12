from django.utils.safestring import mark_safe

from telescope2.web.config import CommandAppConfig

from .bot import Utilities


class BotUtilityConfig(CommandAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telescope2.discord.contrib.utility'

    title = 'Utiltities'
    icon = mark_safe('<i class="bi bi-tools"></i>')

    target = Utilities
