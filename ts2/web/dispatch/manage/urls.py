from django.urls import include, re_path
from django.views.generic.base import RedirectView

from ..public.urls import universal_urls
from . import views


class ManageRedirectView(RedirectView):
    permanent = False
    query_string = True
    pattern_name = 'web:manage.index'


urlpatterns = [
    re_path(r'^$', ManageRedirectView.as_view()),
    re_path(r'^home$', views.index, name='manage.index'),
    re_path(r'^core$', views.core, name='manage.core'),
    re_path(r'^acl$', views.acl_config, name='manage.acl'),
    re_path(r'^logging$', views.logging_config, name='manage.logging'),
    re_path(r'^leave$', views.DeleteServerProfileView.as_view(), name='leave'),
    re_path(r'^reset$', views.ResetServerDataView.as_view(), name='reset'),
    re_path(r'^', include(universal_urls)),
]
