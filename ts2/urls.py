from django.urls import include, path

from ts2admin.site import create_admin_site

admin_site = create_admin_site('telescope2 console', [
    'ts2.discord.admin',
    'ts2.discord.contrib.internet.admin',
    'ts2.web.admin',
])

urlpatterns = [
    path('', include('ts2.web.urls')),
    path('admin/', admin_site.urls),
]
