from django.contrib.admin import AdminSite

from ts2.admin.models import AdminController

from .models import ServerResource


class ServerResourceAdmin(AdminController):
    pass


def register_all(admin_site: AdminSite):
    admin_site.register(ServerResource, ServerResourceAdmin)
