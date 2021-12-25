from pathlib import Path

from decouple import Config, RepositoryEmpty, RepositoryIni

from dougbot2 import VERSION, __version__

APP_NAME = 'telescope2'

VERSION = VERSION

PROJECT_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = PROJECT_DIR.with_name('instance')
RESOURCE_BUILD_DIR = PROJECT_DIR.with_name('build')

secrets_conf = Config(RepositoryIni(INSTANCE_DIR / 'secrets.ini'))
discord_conf = Config(RepositoryIni(INSTANCE_DIR / 'discord.ini'))

try:
    instance_conf = Config(RepositoryIni(INSTANCE_DIR / 'settings.ini'))
except FileNotFoundError:
    instance_conf = Config(RepositoryEmpty())

SECRET_KEY = secrets_conf('SECRET_KEY')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ALLOWED_HOSTS = ['localhost']

# Application definition

INSTALLED_APPS = [
    'cacheops',
    'polymorphic',
    'timezone_field',
    'ts2.admin',
    'django.contrib.admin.apps.SimpleAdminConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'manifest_loader',
    'django_extensions',
    'ts2.web',
    'ts2.web.dispatch.public',
    'ts2.web.dispatch.gateway',
    'ts2.web.dispatch.manage',
    'ts2.discord',
    'ts2.discord.exts.identity',
    'ts2.discord.exts.acl',
    'ts2.discord.contrib.internet',
    'ts2.discord.contrib.poll',
    'ts2.discord.contrib.utility',
    'ts2.discord.contrib.museum',
    'ts2.discord.contrib.ticker',
    'ts2.discord.contrib.debug',
    'ts2.discord.contrib.measurement',
    'ts2.web.contrib.trac',
    'ts2.web.contrib.cupboard',
    'graphene_django',
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
                'ts2.web.contexts.instance_constants',
                'ts2.web.contexts.opengraph',
            ],
        },
    },
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'csp.middleware.CSPMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'ts2.discord.middleware.DiscordContextMiddleware',
]


WSGI_APPLICATION = 'ts2.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': INSTANCE_DIR / 'index.sqlite3',
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

LOGIN_URL = 'web:login'

STATIC_ROOT = PROJECT_DIR.with_name('dist')
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

JWT_DEFAULT_EXP = 300

USER_AGENT = f'Mozilla/5.0 (compatible; telescope2/{__version__}; +https://github.com/tonyzbf/telescope2)'

APPEND_SLASH = True

GRAPHENE = {
    'ATOMIC_MUTATIONS': True,
}


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
        'acl.*': {'ops': {'fetch', 'get'}},
        'profile.*': {'ops': {'fetch', 'get'}},
    }

    CACHE_MIDDLEWARE_ALIAS = 'default'

    return (CACHES, CACHEOPS_REDIS, CACHEOPS_DEFAULTS,
            CACHEOPS, CACHE_MIDDLEWARE_ALIAS)


allowed_guilds: str = instance_conf('SERVER_WHITELIST', None)
if allowed_guilds:
    ALLOWED_GUILDS = {int(s.strip()) for s in allowed_guilds.split(' ')}
else:
    ALLOWED_GUILDS = set()

INSTANCE_CONSTANTS = {
    'BRANDING_FULL': 'telescope2',
    'BRANDING_SHORT': 'ts2',
    'SITE_COLOR': '0d6efd',
    'SITE_DESCRIPTION': '',
    'SITE_TWITTER': '',
}

for k, v in INSTANCE_CONSTANTS.items():
    INSTANCE_CONSTANTS[k] = instance_conf(k, v)

CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = (
    "'self'", "'unsafe-inline'", 'data:',
    'https://fonts.googleapis.com',
    'https://cdn.jsdelivr.net',
    'https://rsms.me',
)
CSP_FONT_SRC = (
    "'self'", 'https://fonts.gstatic.com',
    'https://cdn.jsdelivr.net',
    'https://rsms.me',
)
CSP_CONNECT_SRC = (
    "'self'", 'https://discord.com',
)
CSP_SCRIPT_SRC = (
    "'self'", 'https://cdn.jsdelivr.net',
    'https://cdnjs.cloudflare.com',
)
CSP_WORKER_SRC = ("'self'", 'blob:')
CSP_CHILD_SRC = ("'self'", 'blob:')
CSP_IMG_SRC = (
    "'self'", 'data:', 'https://cdn.discordapp.com',
    'https://upload.wikimedia.org',
)

DISCORD_EAGER_CONNECT = False

MEDIA_ROOT = INSTANCE_DIR / 'media'