from telescope2.web.utils.urls import annotated_re_path

from . import views

app_name = 'utility'

public_views = [
    annotated_re_path(
        r'^timeanddate$', views.timezone_index, name='tz.index',
        title='Time & date', icon='calendar-date',
    ),
]

urlpatterns = [
    *public_views,
]
