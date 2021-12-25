from django.urls import include, path

from .config import find_submodules

app_name = 'ext'


def collect_urls():
    """Find all URLs exposed by bot cogs."""
    urls = []
    for app, module in find_submodules('urls'):
        urls.append(path(f'{app.label}/', include(module)))
    return urls


urlpatterns = collect_urls()
