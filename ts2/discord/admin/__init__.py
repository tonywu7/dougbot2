from pathlib import Path

from django.contrib.admin import AdminSite

from ts2.admin.models import (BaseModelAdmin, register_all_default,
                              register_all_defined)
from ts2.admin.utils.registrar import AdminRegistrar

admin_ = AdminRegistrar()


def register_all(admin_site: AdminSite):
    register_all_defined(admin_site, str(Path(__file__).with_name('views')), __package__, admin_)
    register_all_default(admin_site, 'discord', BaseModelAdmin)
