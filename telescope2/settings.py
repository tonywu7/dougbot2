from pathlib import Path

from decouple import Config, RepositoryIni

from telescope2.utils.logger import config_logging, make_logging_config

config_logging(make_logging_config('telescope2'))

PROJECT_DIR = Path(__file__).resolve().parent
BASE_DIR = PROJECT_DIR.with_name('instance') / 'app'
RESOURCE_BUILD_DIR = PROJECT_DIR.parent / 'build'

instance_conf = Config(RepositoryIni(BASE_DIR / 'settings.ini'))
secrets_conf = Config(RepositoryIni(BASE_DIR / 'secrets.ini'))

SECRET_KEY = secrets_conf('SECRET_KEY')

DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = [
    'channels',
    'telescope2.www.apps.WWWConfig',
    'telescope2.discord.apps.DiscordBotConfig',
    'telescope2.web.apps.WebConfig',
    'django.contrib.admin.apps.SimpleAdminConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'admin2017',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Los_Angeles'
USE_I18N = True
USE_L10N = True
USE_TZ = True


STATIC_ROOT = BASE_DIR / 'static'
STATICFILES_DIRS = [
    PROJECT_DIR / 'www' / 'static',
    RESOURCE_BUILD_DIR,
]

if DEBUG:
    STATICFILES_DIRS += [
        PROJECT_DIR / 'www' / 'bundle',
    ]

STATIC_URL = '/static/'

LOGGING_CONFIG = None

instance_settings = []
instance_secrets = [
    'DISCORD_SECRET',
]

for k in instance_settings:
    globals()[k] = instance_conf(k)
for k in instance_secrets:
    globals()[k] = secrets_conf(k)

ASGI_APPLICATION = 'telescope2.asgi.application'

BRANDING_FULL = 'telescope2'
BRANDING_SHORT = 'ts2'
