from django.utils.functional import classproperty
from django.utils.safestring import mark_safe

from ts2.discord.cog import Gear
from ts2.web.config import CommandAppConfig


class ProfileConfig(CommandAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ts2.discord.ext.profile'

    title = 'Customization'
    icon = mark_safe('<i class="bi bi-sliders"></i>')

    @classproperty
    def target(cls) -> Gear:
        from .bot import Personalize
        return Personalize
