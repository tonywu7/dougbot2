from django.utils.functional import classproperty
from django.utils.safestring import mark_safe

from ts2.discord.cog import Gear
from ts2.web.config import CommandAppConfig


class InternetConfig(CommandAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ts2.discord.contrib.internet'

    title = 'Internet'
    icon = mark_safe('<i class="bi bi-google"></i>')

    @classproperty
    def target(cls) -> Gear:
        from .bot import Internet
        return Internet
