from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from ts2admin.models import AdminController

from .models import BugReport, Feature, User


class DiscordUserAdmin(UserAdmin):
    list_display = ('username', 'snowflake', 'is_staff')
    search_fields = ('username', 'snowflake')

    readonly_fields = ('snowflake',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('info'), {'fields': ('snowflake', 'email')}),
        (_('permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('dates'), {'fields': ('last_login', 'date_joined')}),
    )


class FeatureAdmin(AdminController):
    pass


class BugReportAdmin(AdminController):
    pass


def register_all(admin_site: AdminSite):
    admin_site.register(User, DiscordUserAdmin)
    admin_site.register(Feature, FeatureAdmin)
    admin_site.register(BugReport, BugReportAdmin)
