from django.urls import include, re_path
from django.views.generic.base import RedirectView

from . import views


class IndexRedirectView(RedirectView):
    permanent = False
    query_string = True
    pattern_name = 'web:index'


app_name = 'web'

urlpatterns = [
    re_path(r'^$', views.gateway.index, name='index'),

    re_path(r'^login$', views.gateway.user_login, name='login'),
    re_path(r'^login/continue$', views.gateway.CreateUserView.as_view(), name='create_user'),
    re_path(r'^login/invalid/(?P<reason>[a-z_]+)$', views.gateway.invalid_login, name='login_invalid'),
    re_path(r'^logout$', views.gateway.user_logout, name='logout'),

    re_path(r'^guild/?$', IndexRedirectView.as_view()),
    re_path(r'^guild/join$', views.gateway.join, name='join'),
    re_path(r'^guild/joined$', views.gateway.CreateServerProfileView.as_view(), name='authorized'),
    re_path(r'^guild/(?P<guild_id>[0-9]+)/leave$', views.gateway.DeleteServerProfileView.as_view(), name='leave'),

    re_path(r'^guild/(?P<guild_id>[0-9]+)/index$', views.manage.index, name='manage.index'),
    re_path(r'^guild/(?P<guild_id>[0-9]+)/core$', views.manage.core, name='manage.core'),

    re_path(r'^api/mutation/(?P<schema>(?:[A-Za-z_][A-Za-z0-9]*\.)*[A-Za-z_][A-Za-z0-9]*)/(?P<item_id>[0-9]+)$',
            views.mutation.async_form_save, name='api.mutation'),

    re_path(r'^guild/(?P<guild_id>[0-9]+)/', include('telescope2.discord.urls')),
]
