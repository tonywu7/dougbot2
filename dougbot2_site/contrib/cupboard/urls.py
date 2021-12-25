from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^uploads/(?P<target>.+)', views.get_server_resource, name='server_resource'),
]
