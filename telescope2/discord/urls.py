from pathlib import Path

from django.urls import include, path

from telescope2.utils.importutil import iter_module_tree

from .apps import DiscordBotConfig

app_name = 'plugins'


def collect_urls():
    root = DiscordBotConfig.name
    urls = []
    for plugin_name, in iter_module_tree(str(Path(__file__).with_name('contrib')), 1):
        try:
            included = include(f'{root}.contrib.{plugin_name}.urls')
        except ModuleNotFoundError:
            continue
        urls.append(path(f'{plugin_name}/', included))
    return urls


urlpatterns = collect_urls()