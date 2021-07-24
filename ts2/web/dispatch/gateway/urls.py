from django.urls import re_path
from django.views.generic.base import RedirectView

from . import views


class IndexRedirectView(RedirectView):
    permanent = False
    query_string = True
    pattern_name = 'web:index'


urlpatterns = [
    re_path(r'^login$', views.user_login, name='login'),
    re_path(r'^login/continue$', views.CreateUserView.as_view(), name='create_user'),
    re_path(r'^login/invalid/(?P<reason>[a-z_]+)$', views.invalid_login, name='login_invalid'),
    re_path(r'^logout$', views.user_logout, name='logout'),
    re_path(r'^guild/?$', IndexRedirectView.as_view()),
    re_path(r'^guild/join$', views.join, name='join'),
    re_path(r'^guild/joined$', views.CreateServerProfileView.as_view(), name='authorized'),
]
