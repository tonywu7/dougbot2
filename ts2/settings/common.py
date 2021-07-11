from pathlib import Path

from decouple import Config, RepositoryIni

APP_NAME = 'telescope2'

__version__ = '0.0.1'

PROJECT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = PROJECT_DIR.with_name('instance')
RESOURCE_BUILD_DIR = PROJECT_DIR / 'web' / 'bundle' / 'build'

secrets_conf = Config(RepositoryIni(BASE_DIR / 'secrets.ini'))
discord_conf = Config(RepositoryIni(BASE_DIR / 'discord.ini'))

SECRET_KEY = secrets_conf('SECRET_KEY')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ALLOWED_HOSTS = ['localhost']

# Application definition

INSTALLED_APPS = [
    'cacheops',
    'polymorphic',
    'rest_framework',
    'ts2admin',
    'django.contrib.admin.apps.SimpleAdminConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'ts2.web.apps.WebConfig',
    'ts2.discord.apps.DiscordBotConfig',
    'ts2.discord.preferences.apps.ConfConfig',
    'ts2.discord.contrib.internet.apps.InternetConfig',
    'ts2.discord.contrib.utility.apps.BotUtilityConfig',
    'ts2.discord.contrib.museum.apps.MuseumConfig',
    'ts2.discord.contrib.integration.apps.IntegrationConfig',
    'ts2.discord.contrib.debugging.apps.DebuggingConfig',
    'channels',
]

ROOT_URLCONF = 'ts2.urls'

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
                'ts2.web.contexts.application_info',
                'ts2.web.contexts.site_info',
                'ts2.web.contexts.user_info',
                'ts2.web.contexts.discord_info',
            ],
        },
    },
]

WSGI_APPLICATION = 'ts2.wsgi.application'


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

STATIC_ROOT = BASE_DIR / 'static'
STATICFILES_DIRS = [
    RESOURCE_BUILD_DIR,
    PROJECT_DIR / 'web' / 'static',
]

STATIC_URL = '/static/'

LOGGING_CONFIG = None

discord_secrets = [
    'DISCORD_CLIENT_ID',
    'DISCORD_CLIENT_SECRET',
    'DISCORD_BOT_TOKEN',
]

for k in discord_secrets:
    globals()[k] = discord_conf(k)

ASGI_APPLICATION = 'ts2.asgi.application'

BRANDING_FULL = 'telescope2'
BRANDING_SHORT = 'telescope2'

JWT_DEFAULT_EXP = 300

USER_AGENT = f'Mozilla/5.0 (compatible; telescope2/{__version__}; +https://github.com/tonyzbf/telescope2)'

APPEND_SLASH = True


def config_caches(redis_host):
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': f'redis://{redis_host}:6379/1',
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
        },
        'discord': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': f'redis://{redis_host}:6379/3',
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
        },
        'jinja2': {
            'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
            'LOCATION': '127.0.0.1:11211',
        },
    }

    CACHEOPS_REDIS = f'redis://{redis_host}:6379/2'

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

    return (CACHES, CACHEOPS_REDIS, CACHEOPS_DEFAULTS,
            CACHEOPS, CACHE_MIDDLEWARE_ALIAS)
