from django.urls import re_path
from django.views.generic import RedirectView

from . import views


class IndexRedirectView(RedirectView):
    permanent = False
    query_string = True
    pattern_name = 'web:index'


universal_urls = [
    re_path(r'^features/?$', views.feature_tracker, name='features'),
]

urlpatterns = [
    re_path(r'^$', views.index, name='index'),
    *universal_urls,
]
