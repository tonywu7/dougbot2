from django.apps import apps
from django.urls import include, path

from .config import CommandAppConfig

app_name = 'ext'


def collect_urls():
    """Find all URLs exposed by bot cogs."""
    urls = []
    for app in apps.get_app_configs():
        if not isinstance(app, CommandAppConfig):
            continue
        try:
            included = include(f'{app.module.__name__}.urls')
        except ModuleNotFoundError:
            continue
        urls.append(path(f'{app.label}/', included))
    return urls


urlpatterns = collect_urls()
