from django.urls import re_path

from ts2.web.config import annotated_re_path

from . import views

app_name = 'internet'

public_views = [
    annotated_re_path(
        r'^timeanddate$', views.timezone_index, name='tz.index',
        title='Time & date', icon='<i class="bi bi-calendar-date"></i>',
    ),
]

urlpatterns = [
    *public_views,
    re_path(
        r'^api/v1/roletimezone/(?P<pk>[0-9]+)$',
        views.RoleTimezoneView.as_view(),
        name='api.guild.contrib.internet.roletimezone',
    ),
    re_path(
        r'^api/v1/roletimezones$',
        views.RoleTimezoneListView.as_view(),
        name='api.guild.contrib.internet.roletimezone.list',
    ),
]
