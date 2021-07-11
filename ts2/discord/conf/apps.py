from django.utils.functional import classproperty
from django.utils.safestring import mark_safe

from ts2.discord.extension import Gear
from ts2.web.config import CommandAppConfig


class ConfConfig(CommandAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ts2.discord.conf'

    title = 'Settings'
    icon = mark_safe('<i class="bi bi-sliders"></i>')

    @classproperty
    def target(cls) -> Gear:
        from .bot import Conf
        return Conf
