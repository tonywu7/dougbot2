import os

from decouple import Config, RepositoryIni

from .common import ALLOWED_HOSTS, INSTANCE_DIR, config_caches
from .production import *  # noqa: F403, F401

if os.getenv('NO_CACHE', 'false') == 'false':
    (CACHES, CACHEOPS_REDIS, CACHEOPS_DEFAULTS,
     CACHEOPS, CACHE_MIDDLEWARE_ALIAS) = config_caches('redis')

ALLOWED_HOSTS = ALLOWED_HOSTS

try:
    server_conf = Config(RepositoryIni(INSTANCE_DIR / 'server.ini'))
except FileNotFoundError:
    pass
else:
    allowed_hosts = server_conf('ALLOWED_HOSTS', None)
    if allowed_hosts:
        ALLOWED_HOSTS += allowed_hosts.split(' ')
