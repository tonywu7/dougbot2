import os

from .common import config_caches
from .production import *  # noqa: F403, F401

if os.getenv('NO_CACHE', 'false') == 'false':
    (CACHES, CACHEOPS_REDIS, CACHEOPS_DEFAULTS,
     CACHEOPS, CACHE_MIDDLEWARE_ALIAS) = config_caches('redis')
