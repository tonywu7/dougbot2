from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^$', views.index, name='web.index'),
    re_path(r'^login$', views.user_login, name='web.login'),
    re_path(r'^login/continue$', views.CreateUserView.as_view(), name='web.create_user'),
    re_path(r'^login/invalid/(?P<reason>[a-z_]+)$', views.invalid_login, name='web.login_invalid'),
    re_path(r'^logout$', views.user_logout, name='web.logout'),
    re_path(r'^invite$', views.invite, name='web.invite'),
    re_path(r'^authorized$', views.authorized, name='web.authorized'),
]
