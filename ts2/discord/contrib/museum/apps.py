from django.utils.functional import classproperty
from django.utils.safestring import mark_safe

from ts2.web.config import CommandAppConfig

from ...extension import Gear


class MuseumConfig(CommandAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ts2.discord.contrib.museum'

    title = 'Archival'
    icon = mark_safe('<i class="bi bi-archive-fill"></i>')

    @classproperty
    def target(cls) -> Gear:
        from .bot import Museum
        return Museum
