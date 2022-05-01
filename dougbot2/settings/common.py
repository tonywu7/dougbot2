from pathlib import Path

from decouple import Config, RepositoryIni

from dougbot2 import VERSION, __version__

APP_NAME = 'dougbot2'

VERSION = VERSION

PROJECT_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = PROJECT_DIR.with_name('instance')
RESOURCE_BUILD_DIR = PROJECT_DIR.with_name('build')

secrets_conf = Config(RepositoryIni(INSTANCE_DIR / 'secrets.ini'))
SECRET_KEY = secrets_conf('SECRET_KEY')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

ALLOWED_HOSTS = ['localhost']

# Application definition

INSTALLED_APPS = [
    'cacheops',
    'polymorphic',
    'timezone_field',
    'dougbot2.admin',
    'django.contrib.admin.apps.SimpleAdminConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'manifest_loader',
    'django_extensions',
    'dougbot2',
    'dougbot2.utils.apps',
    'dougbot2.exts.autodoc',
    'dougbot2.exts.errorfluff',
    'dougbot2.exts.firewall',
    'dougbot2.exts.papertrail',
    'dougbot2.contrib.controls',
    'dougbot2.contrib.debug',
    'dougbot2.contrib.help',
    'dougbot2.contrib.internet',
    'dougbot2.contrib.museum',
    'dougbot2.contrib.replyutils',
    'dougbot2.contrib.poll',
    'dougbot2.contrib.remarks',
    'dougbot2.contrib.summon',
    'dougbot2.contrib.surveillance',
    'dougbot2.contrib.telemetry',
    'dougbot2.contrib.ticker',
    'dougbot2.contrib.timeanddate',
    'dougbot2.contrib.utility',
]

# ROOT_URLCONF = 'dougbot2.urls'

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
]


# WSGI_APPLICATION = 'dougbot2.wsgi.application'


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

# AUTH_USER_MODEL = 'web.User'

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

# LOGIN_URL = 'web:login'

STATIC_ROOT = PROJECT_DIR.with_name('dist')
STATICFILES_DIRS = [
    RESOURCE_BUILD_DIR,
    # PROJECT_DIR / 'web' / 'static',
]

STATIC_URL = '/static/'

LOGGING_CONFIG = None

# ASGI_APPLICATION = 'dougbot2.asgi.application'

JWT_DEFAULT_EXP = 300

USER_AGENT = f'Mozilla/5.0 (compatible; dougbot2/{__version__}; +https://github.com/tonyzbf/dougbot2)'

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
        'dougbot2.*': {'ops': {'fetch', 'get'}},
        'firewall.*': {'ops': {'fetch', 'get'}},
        'poll.*': {'ops': {'fetch', 'get'}},
        'ticker.*': {'ops': {'fetch', 'get'}},
        'timeanddate.*': {'ops': {'fetch', 'get'}},
    }

    CACHE_MIDDLEWARE_ALIAS = 'default'

    return (CACHES, CACHEOPS_REDIS, CACHEOPS_DEFAULTS,
            CACHEOPS, CACHE_MIDDLEWARE_ALIAS)


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

MEDIA_ROOT = INSTANCE_DIR / 'media'
