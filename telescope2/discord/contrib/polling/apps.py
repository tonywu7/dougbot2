from django.utils.functional import classproperty
from django.utils.safestring import mark_safe

from telescope2.discord.extension import Gear
from telescope2.web.config import CommandAppConfig


class PollConfig(CommandAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telescope2.discord.contrib.polling'

    title = 'Polling'
    icon = mark_safe('<i class="bi bi-ui-checks"></i>')

    @classproperty
    def target(cls) -> Gear:
        from .bot import Poll
        return Poll
