from django.urls import re_path

from . import views

universal_urls = [
    re_path(r'^features/?$', views.feature_tracker, name='features'),
]

urlpatterns = [
    re_path(r'^$', views.index, name='index'),
    re_path(r'^index/?$', views.index, name='index'),
    *universal_urls,
]
