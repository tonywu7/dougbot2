from django.conf import settings
from django.urls import include, re_path

from .._compat.graphql_django import GraphQLView_
from . import schema, views

app_name = 'web'

urlpatterns = [
    re_path(r'.*\.html?', views.remove_suffix, name='suffix_redirect'),
    re_path(r'', include('ts2.web.dispatch.public.urls')),
    re_path(r'^gateway/', include('ts2.web.dispatch.gateway.urls')),
    re_path(r'^guild/(?P<guild_id>[0-9]+)/', include('ts2.web.dispatch.manage.urls')),
    re_path(r'^guild/(?P<guild_id>[0-9]+)/server/', include('ts2.discord.urls')),
    re_path(r'^graphql$', name='api',
            view=GraphQLView_.as_view(graphiql=settings.DEBUG, schema=schema.schema)),
]
