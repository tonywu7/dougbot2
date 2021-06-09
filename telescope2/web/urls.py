from django.urls import re_path
from django.views.generic.base import RedirectView

from . import views


class IndexRedirectView(RedirectView):
    permanent = False
    query_string = True
    pattern_name = 'web.index'


urlpatterns = [
    re_path(r'^$', views.index, name='web.index'),

    re_path(r'^login$', views.user_login, name='web.login'),
    re_path(r'^login/continue$', views.CreateUserView.as_view(), name='web.create_user'),
    re_path(r'^login/invalid/(?P<reason>[a-z_]+)$', views.invalid_login, name='web.login_invalid'),
    re_path(r'^logout$', views.user_logout, name='web.logout'),

    re_path(r'^guild/?$', IndexRedirectView.as_view()),
    re_path(r'^guild/join$', views.join, name='web.join'),
    re_path(r'^guild/joined$', views.CreateServerProfileView.as_view(), name='web.authorized'),
    re_path(r'^guild/(?P<guild_id>[0-9]+)/manage$', views.index, name='web.manage'),
    re_path(r'^guild/(?P<guild_id>[0-9]+)/leave$', views.DeleteServerProfileView.as_view(), name='web.leave'),
]
