from telescope2.utils.urls import annotated_re_path

from . import views

app_name = 'museum'

public_views = [
    annotated_re_path(
        r'^museum$', views.museum_view, name='museum.index',
        title='Museum', icon='<i class="bi bi-pin-angle"></i>',
    ),
]

urlpatterns = [
    *public_views,
]
