from django.apps import AppConfig


class TelemetryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dougbot2.contrib.telemetry'
    default = True
