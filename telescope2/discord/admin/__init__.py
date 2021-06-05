from django.contrib.admin import AdminSite

from telescope2.management.utils import AdminRegistrar

from .base import BaseModelAdmin, register_all_default, register_all_defined

admin_ = AdminRegistrar()


def register_all(admin_site: AdminSite):
    register_all_defined(admin_site, admin_)
    register_all_default(admin_site, 'discord', BaseModelAdmin)
