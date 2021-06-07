from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


class DiscordUserAdmin(UserAdmin):
    list_display = ('username', 'discord_id', 'is_staff')
    search_fields = ('username', 'discord_id')

    readonly_fields = ('discord_id',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('info'), {'fields': ('discord_id', 'email')}),
        (_('permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('dates'), {'fields': ('last_login', 'date_joined')}),
    )


def register_all(admin_site: AdminSite):
    admin_site.register(User, DiscordUserAdmin)
