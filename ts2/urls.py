from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import include, path
from django.views.generic.base import RedirectView

from ts2admin.site import create_admin_site

admin_site = create_admin_site('telescope2 console', [
    'ts2.discord.admin',
    'ts2.web.admin',
])

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='web:index')),
    path('web/', include('ts2.web.urls')),
    path('admin/', admin_site.urls),
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.ico'))),
]
