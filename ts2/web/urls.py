from django.conf import settings
from django.urls import include, re_path
from django.views.generic.base import RedirectView
from graphene_django.views import GraphQLView

from . import schema, views


class IndexRedirectView(RedirectView):
    permanent = False
    query_string = True
    pattern_name = 'web:index'


class ManageRedirectView(RedirectView):
    permanent = False
    query_string = True
    pattern_name = 'web:manage.index'


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
    re_path(r'^guild/(?P<guild_id>[0-9]+)/reset$', views.gateway.ResetServerDataView.as_view(), name='reset'),

    re_path(r'^guild/(?P<guild_id>[0-9]+)/index$', views.manage.index, name='manage.index'),
    re_path(r'^guild/(?P<guild_id>[0-9]+)/core$', views.manage.core, name='manage.core'),
    re_path(r'^guild/(?P<guild_id>[0-9]+)/acl$', views.manage.acl_config, name='manage.acl'),
    re_path(r'^guild/(?P<guild_id>[0-9]+)/logging$', views.manage.logging_config, name='manage.logging'),

    re_path(r'^guild/(?P<guild_id>[0-9]+)/', include('ts2.discord.urls')),
    re_path(r'^guild/(?P<guild_id>[0-9]+)/?$', ManageRedirectView.as_view()),

    re_path(
        r'^graphql$', name='api',
        view=GraphQLView.as_view(graphiql=settings.DEBUG, schema=schema.schema),
    ),
]
