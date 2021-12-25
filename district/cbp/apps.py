from django.utils.functional import classproperty
from django.utils.safestring import mark_safe

from ts2.discord.cog import Gear
from ts2.discord.config import CommandAppConfig


class CBPConfig(CommandAppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'district.cbp'
    default = True

    title = ...
    icon = mark_safe(...)

    @classproperty
    def target(cls) -> Gear:
        from .bot import CBP
        return CBP
