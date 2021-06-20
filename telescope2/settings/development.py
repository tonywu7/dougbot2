from .common import *  # noqa: F403, F401
from .common import PROJECT_DIR, STATICFILES_DIRS

DEBUG = True

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'telescope2.web.middleware.DiscordContextMiddleware',
]

STATICFILES_DIRS += [
    PROJECT_DIR / 'web' / 'bundle',
]
