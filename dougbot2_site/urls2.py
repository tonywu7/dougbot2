from csp.decorators import csp_exempt
from django.conf import settings
from django.urls import include, re_path

from . import schema
from ._compat.graphql_django import GraphQLView_

app_name = 'web'

urlpatterns = [
    re_path(r'', include('ts2.web.dispatch.public.urls')),
    re_path(r'^gateway/', include('ts2.web.dispatch.gateway.urls')),
    re_path(r'^guild/(?P<guild_id>[0-9]+)/', include('ts2.web.dispatch.manage.urls')),
    re_path(r'^guild/(?P<guild_id>[0-9]+)/server/', include('ts2.discord.urls')),
    re_path(r'^guild/(?P<guild_id>[0-9]+)/media/', include('ts2.web.contrib.cupboard.urls')),
    re_path(r'^graphql$', name='api',
            view=csp_exempt(GraphQLView_.as_view(graphiql=settings.DEBUG, schema=schema.schema))),
]
