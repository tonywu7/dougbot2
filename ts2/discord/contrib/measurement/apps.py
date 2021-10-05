from django.utils.functional import classproperty
from django.utils.safestring import mark_safe

from ts2.discord.cog import Gear
from ts2.discord.config import CommandAppConfig


class MeasurementConfig(CommandAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ts2.discord.contrib.measurement'
    default = True

    title = 'Measurement'
    icon = mark_safe('<i class="bi bi-rulers"></i>')

    @classproperty
    def target(cls) -> Gear:
        from .bot import Measurement
        return Measurement
