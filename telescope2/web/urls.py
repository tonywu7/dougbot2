from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^oauth2/$', views.invite, name='web.invite'),
    re_path(r'^authorized/$', views.authorized, name='web.authorized'),
    re_path(r'^$', views.index, name='web.index'),
]
