from django.utils.functional import classproperty
from django.utils.safestring import mark_safe

from ts2.discord.cog import Gear
from ts2.web.config import CommandAppConfig


class IntegrationConfig(CommandAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ts2.discord.contrib.integration'

    title = 'Integration'
    icon = mark_safe('<i class="bi bi-broadcast-pin"></i>')

    @classproperty
    def target(cls) -> Gear:
        from .bot import Integration
        return Integration
