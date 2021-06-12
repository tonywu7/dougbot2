from pathlib import Path

from django.contrib.admin import AdminSite

from admin2017.models import (BaseModelAdmin, BasePolymorphicAdmin,
                              register_all_default, register_all_defined,
                              register_all_polymorphic)
from admin2017.utils.registrar import AdminRegistrar

from ..models import Entity
from .views.entity import EntityRootAdmin

admin_ = AdminRegistrar()


def register_all(admin_site: AdminSite):
    admin_site.register(Entity, EntityRootAdmin)
    register_all_defined(admin_site, str(Path(__file__).with_name('views')), __package__, admin_)
    register_all_polymorphic(admin_site, 'discord', Entity, BasePolymorphicAdmin)
    register_all_default(admin_site, 'discord', BaseModelAdmin)
