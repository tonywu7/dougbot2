from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^login$', views.login, name='web.login'),
    re_path(r'^login/continue$', views.logged_in, name='web.logged_in'),
    re_path(r'^invite$', views.invite, name='web.invite'),
    re_path(r'^authorized$', views.authorized, name='web.authorized'),
    re_path(r'^$', views.index, name='web.index'),
]
