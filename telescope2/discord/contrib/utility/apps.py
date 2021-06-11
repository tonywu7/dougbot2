from django.utils.functional import classproperty

from telescope2.web.utils.config import CommandAppConfig


class BotUtilityConfig(CommandAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telescope2.discord.contrib.utility'

    @classproperty
    def title(cls):
        return 'Utiltities'

    @classproperty
    def icon(cls):
        return '<i class="bi bi-tools"></i>'
