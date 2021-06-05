from admin2017.site import create_admin_site
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import include, path
from django.views.generic.base import RedirectView

admin_site = create_admin_site('telescope2 console', [
    'telescope2.discord.admin',
])

urlpatterns = [
    path('bot/', include('telescope2.discord.urls')),
    path('admin/', admin_site.urls),
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.ico'))),
]
