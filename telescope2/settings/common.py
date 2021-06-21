from pathlib import Path

from decouple import Config, RepositoryIni

from telescope2.utils.logger import config_logging, make_logging_config

APP_NAME = 'telescope2'

__version__ = '0.0.1'

config_logging(make_logging_config(APP_NAME))

PROJECT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = PROJECT_DIR.with_name('instance') / 'app'
RESOURCE_BUILD_DIR = PROJECT_DIR / 'web' / 'bundle' / 'build'

instance_conf = Config(RepositoryIni(BASE_DIR / 'settings.ini'))
secrets_conf = Config(RepositoryIni(BASE_DIR / 'secrets.ini'))

SECRET_KEY = secrets_conf('SECRET_KEY')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ALLOWED_HOSTS = ['localhost']

# Application definition

INSTALLED_APPS = [
    'cacheops',
    'polymorphic',
    'rest_framework',
    'telescope2_admin',
    'django.contrib.admin.apps.SimpleAdminConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'telescope2.web.apps.WebConfig',
    'telescope2.discord.apps.DiscordBotConfig',
    'telescope2.discord.contrib.debugging.apps.DebuggingConfig',
    'telescope2.discord.contrib.utility.apps.BotUtilityConfig',
    'telescope2.discord.contrib.polling.apps.PollConfig',
    'telescope2.discord.contrib.museum.apps.MuseumConfig',
    'telescope2.discord.contrib.integration.apps.IntegrationConfig',
    'telescope2.discord.contrib.internet.apps.InternetConfig',
    'channels',
]

ROOT_URLCONF = 'telescope2.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'telescope2.web.contexts.application_info',
                'telescope2.web.contexts.site_info',
                'telescope2.web.contexts.user_info',
                'telescope2.web.contexts.discord_info',
            ],
        },
    },
]

WSGI_APPLICATION = 'telescope2.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'index.sqlite3',
    },
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_USER_MODEL = 'web.User'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    },
    'discord': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/3',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    },
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'Strict'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Los_Angeles'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LOGIN_URL = '/web'

STATIC_ROOT = PROJECT_DIR / 'web' / 'bundle' / 'dist'
STATICFILES_DIRS = [
    RESOURCE_BUILD_DIR,
    PROJECT_DIR / 'web' / 'static',
]

STATIC_URL = '/static/'

LOGGING_CONFIG = None

instance_settings = []
instance_secrets = [
    'DISCORD_CLIENT_ID',
    'DISCORD_CLIENT_SECRET',
    'DISCORD_BOT_TOKEN',
]

for k in instance_settings:
    globals()[k] = instance_conf(k)
for k in instance_secrets:
    globals()[k] = secrets_conf(k)

ASGI_APPLICATION = 'telescope2.asgi.application'

BRANDING_FULL = 'telescope2'
BRANDING_SHORT = 'ts2'

JWT_DEFAULT_EXP = 300

USER_AGENT = f'Mozilla/5.0 (compatible; telescope2/{__version__}; +https://github.com/tonyzbf/telescope2)'


CACHEOPS_REDIS = 'redis://localhost:6379/2'

CACHEOPS_DEFAULTS = {
    'timeout': 60 * 60,
}

CACHEOPS = {
    'auth.user': {'ops': 'get', 'timeout': 60 * 15},
    'auth.*': {'ops': ('fetch', 'get')},
    'auth.permission': {'ops': 'all'},
    'discord.*': {'ops': {'fetch', 'get'}},
}

CACHE_MIDDLEWARE_ALIAS = 'default'

APPEND_SLASH = True
