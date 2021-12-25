from dougbot2.utils.logger import config_logging, make_logging_config

from .common import *  # noqa: F403, F401
from .common import APP_NAME, config_caches

DEBUG = True
config_logging(make_logging_config(APP_NAME, level=10))

(CACHES, CACHEOPS_REDIS, CACHEOPS_DEFAULTS,
 CACHEOPS, CACHE_MIDDLEWARE_ALIAS) = config_caches('localhost')
