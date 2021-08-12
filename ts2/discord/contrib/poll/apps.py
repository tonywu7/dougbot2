from django.utils.functional import classproperty
from django.utils.safestring import mark_safe

from ts2.discord.cog import Gear
from ts2.discord.config import CommandAppConfig


class PollConfig(CommandAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ts2.discord.contrib.poll'
    default = True

    title = 'Polling'
    icon = mark_safe('<i class="bi bi-bar-chart-line-fill"></i>')

    @classproperty
    def target(cls) -> Gear:
        from .bot import Poll
        return Poll