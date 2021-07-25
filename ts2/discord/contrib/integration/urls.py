from ts2.discord.config import annotated_re_path

from . import views

app_name = 'integration'

public_views = [
    annotated_re_path(
        r'^twitch$', views.twitch_view, name='twitch.index',
        title='Twitch', icon='<i class="bi bi-twitch"></i>',
    ),
    annotated_re_path(
        r'^reddit$', views.twitch_view, name='reddit.index',
        title='Reddit', icon='<i class="bi bi-reddit"></i>',
    ),
]

urlpatterns = [
    # *public_views,
]
