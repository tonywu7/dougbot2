from django.urls import re_path
from django.views.generic import RedirectView

from . import views


class IndexRedirectView(RedirectView):
    permanent = False
    query_string = True
    pattern_name = 'web:index'


universal_urls = [
    re_path(r'^features/?$', views.feature_tracker, name='features'),
    re_path(r'^bug-report/?$', views.BugReportView.as_view(), name='bugreport'),
    re_path(r'^delete-my-account/?$', views.InfoRemovalRequestView.as_view(), name='removal'),
    re_path(r'^blog/(?P<dest>.+)', views.blog, name='blog'),

    re_path(r'^about$', RedirectView.as_view(pattern_name='web:blog', permanent=True),
            kwargs={'dest': 'about'}, name='about'),
    re_path(r'^privacy$', RedirectView.as_view(pattern_name='web:blog', permanent=True),
            kwargs={'dest': 'privacy'}, name='privacy'),
]

urlpatterns = [
    re_path(r'^$', views.index, name='index'),
    *universal_urls,
]
