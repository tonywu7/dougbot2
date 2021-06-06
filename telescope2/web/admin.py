from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin

from .models import User


def register_all(admin_site: AdminSite):
    admin_site.register(User, UserAdmin)
