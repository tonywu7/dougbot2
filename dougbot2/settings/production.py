import os

from ..utils.logger import config_logging, make_logging_config
from . import common
from .common import APP_NAME, STATIC_ROOT, config_caches

DEBUG = False
config_logging(make_logging_config(APP_NAME, level=20))

if os.getenv("NO_CACHE", "false") == "false":
    (
        CACHES,
        CACHEOPS_REDIS,
        CACHEOPS_DEFAULTS,
        CACHEOPS,
        CACHE_MIDDLEWARE_ALIAS,
    ) = config_caches("localhost")

MANIFEST_LOADER = {
    "output_dir": STATIC_ROOT,
    "cache": True,
}

globals().update(vars(common))
