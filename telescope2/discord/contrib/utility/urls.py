from telescope2.web.config import annotated_re_path

from . import views

app_name = 'utility'

public_views = [
    annotated_re_path(
        r'^timeanddate$', views.timezone_index, name='tz.index',
        title='Time & date', icon='<i class="bi bi-calendar-date"></i>',
    ),
]

urlpatterns = [
    *public_views,
]
