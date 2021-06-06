from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^oauth2/$', views.invite, name='bot.invite'),
    re_path(r'^authorized/$', views.authorized, name='bot.authorized'),
    re_path(r'^$', views.index, name='bot.index'),
]
