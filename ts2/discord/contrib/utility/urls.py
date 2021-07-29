from ts2.discord.config import annotated_re_path

from . import views

app_name = 'utility'

public_views = [
    annotated_re_path(
        r'^suggestions$', views.suggestions_view, name='suggestion.index',
        title='Suggestions 🚧', icon='<i class="bi bi-inbox"></i>',
    ),
    annotated_re_path(
        r'^polling$', views.polling_view, name='polling.index',
        title='Polling 🚧', icon='<i class="bi bi-hand-thumbs-up"></i>',
    ),
]

urlpatterns = [
    *public_views,
]
