def list_versions() -> dict[str, str]:
    from platform import python_version

    from aiohttp import __version__ as aiohttp_version
    from discord import __version__ as discord_version
    from django import __version__ as django_version
    from jinja2 import __version__ as jinja_version

    from .common import APP_NAME, __version__

    return {
        APP_NAME: __version__,
        'python': python_version(),
        'discord.py': discord_version,
        'django': django_version,
        'aiohttp': aiohttp_version,
        'jinja': jinja_version,
    }
