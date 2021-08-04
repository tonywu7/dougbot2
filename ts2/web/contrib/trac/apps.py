from django.utils.functional import classproperty
from django.utils.safestring import mark_safe

from ts2.discord.cog import Gear
from ts2.discord.config import CommandAppConfig


class TracConfig(CommandAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ts2.web.contrib.trac'

    title = 'Trac'
    icon = mark_safe('<i class="bi bi-kanban"></i>')
    hidden = True

    @classproperty
    def target(cls) -> Gear:
        from .bot import Trac
        return Trac
