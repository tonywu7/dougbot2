import os

from ts2.utils.logger import config_logging, make_logging_config

from .common import *  # noqa: F403, F401
from .common import APP_NAME, config_caches

DEBUG = False
config_logging(make_logging_config(APP_NAME, level=20))

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'ts2.web.middleware.DiscordContextMiddleware',
]

if os.getenv('NO_CACHE', 'false') == 'false':
    (CACHES, CACHEOPS_REDIS, CACHEOPS_DEFAULTS,
     CACHEOPS, CACHE_MIDDLEWARE_ALIAS) = config_caches('redis')
