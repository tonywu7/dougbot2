from django.apps import AppConfig


class NoReplyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dougbot2.contrib.noreply'
    default = True
