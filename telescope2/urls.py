from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import include, path
from django.views.generic.base import RedirectView

from .management.admin import admin_site

urlpatterns = [
    path('bot/', include('telescope2.discord.urls')),
    path('admin/', admin_site.urls),
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.ico'))),
]
