from django.utils.functional import classproperty
from django.utils.safestring import mark_safe

from ...cog import Gear
from ...config import CommandAppConfig


class IdentityConfig(CommandAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ts2.discord.ext.identity'
    default = True

    title = 'Customization'
    icon = mark_safe('<i class="bi bi-sliders"></i>')

    @classproperty
    def target(cls) -> Gear:
        from .bot import Personalize
        return Personalize
