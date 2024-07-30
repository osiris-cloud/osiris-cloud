"""
https://docs.djangoproject.com/en/4.2/topics/settings/
https://docs.djangoproject.com/en/4.2/ref/settings/
https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/
"""

import os
import yaml
from pathlib import Path

from dotenv import load_dotenv, find_dotenv
from str2bool import str2bool
from dataclasses import dataclass
from urllib.parse import urlparse

import logging

load_dotenv(override=True if os.environ.get('DEBUG') is None else False)

DEBUG = str2bool(os.environ.get('DEBUG'))
if DEBUG is None:
    DEBUG = True

print(f'# DEBUG MODE -> {DEBUG}')

if DEBUG == False:
    import sentry_sdk

    sentry_sdk.init(
        dsn="https://d140ad735d6170ed7a240ad5cefe7670@o4507397577375744.ingest.us.sentry.io/4507397582422016",
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
    )

logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)

ALGOLIA = {
    'APPLICATION_ID': os.environ.get('ALGOLIA_APP_ID'),
    'API_KEY': os.environ.get('ALGOLIA_API_KEY'),
}

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class Env:
    nyu_client_id = os.getenv('NYU_CLIENT_ID')
    nyu_client_secret = os.getenv('NYU_CLIENT_SECRET')
    nyu_openid_meta = os.getenv('NYU_META_URL')

    github_client_id = os.getenv('GITHUB_CLIENT_ID')
    github_client_secret = os.getenv('GITHUB_CLIENT_SECRET')

    cf_storage_url = os.getenv('CF_STORAGE_URL')
    cf_access_key = os.getenv('CF_ACCESS_KEY')
    cf_secret_key = os.getenv('CF_SECRET_KEY')

    rabbitmq_url = os.getenv('MQ_URL')

    k8s_config = {}
    k8s_url = ''
    k8s_ws_url = ''
    k8s_token = ''

    def __post_init__(self):
        kubeconfig_path = os.path.join(BASE_DIR, 'kubeconfig.yaml')
        if os.path.exists(kubeconfig_path):
            with open(kubeconfig_path, 'r') as file:
                self.k8s_config = yaml.safe_load(file)
                self.k8s_url = self.k8s_config['clusters'][0]['cluster']['server']
                self.k8s_token = self.k8s_config['users'][0]['user']['token']
                url = urlparse(self.k8s_url)
                self.k8s_ws_url = 'ws://' if url.scheme == 'http' else 'wss://' + url.netloc + url.path


env = Env()

SECRET_KEY = os.environ.get('SECRET_KEY')

ALLOWED_HOSTS = ['osiriscloud.io', 'staging.osiriscloud.io', 'localhost']
CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'https://osiriscloud.io', 'https://staging.osiriscloud.io']

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_celery_results",
    'rest_framework',
    'rest_framework.authtoken',
    "algoliasearch_django",
    "main",
    "apps.api",
    "apps.dns_manager",
    "apps.ip_manager",
    "apps.k8s",
    "apps.oauth",
    "apps.users",
    "apps.vm",

    'drf_spectacular',
    'django_api_gen',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "main.middleware.RemoveSlashMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

APPEND_SLASH = False

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

AUTH_USER_MODEL = "users.User"
AUTHENTICATION_BACKENDS = ['apps.oauth.backend.AuthBackend']

LOGIN_URL = "/login"
LOGIN_REDIRECT_URL = "/dashboard"
LOGOUT_REDIRECT_URL = "/login"

ROOT_URLCONF = "core.urls"
UI_TEMPLATES = os.path.join(BASE_DIR, 'templates')

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [UI_TEMPLATES],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

DATABASE_CONNECTION_POOLING = False
if DEBUG == False:
    DATABASES = {
        'default': {
            'ENGINE': 'mssql',
            'NAME': DB_NAME,
            'USER': DB_USERNAME,
            'PASSWORD': DB_PASS,
            'HOST': DB_HOST,
            'PORT': DB_PORT,
            'OPTIONS': {
                'driver': 'ODBC Driver 17 for SQL Server',
            },
        },
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'db.sqlite3',
        }
    }

# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

MEDIA_URL = 'media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

########################################
# ### Async Tasks (Celery) Settings ###

# CELERY_SCRIPTS_DIR = os.path.join(BASE_DIR, "tasks_scripts")
#
# CELERY_LOGS_URL = "/tasks_logs/"
# CELERY_LOGS_DIR = os.path.join(BASE_DIR, "tasks_logs")
#
CELERY_BROKER_URL = env.rabbitmq_url
CELERY_RESULT_BACKEND = "django-db"

CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_CACHE_BACKEND = "django-cache"

CELERY_RESULT_EXTENDED = True
CELERY_RESULT_EXPIRES = 60 * 60 * 24 * 30  # Results expire after 1 month
CELERY_ACKS_LATE = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_ALWAYS_EAGER = DEBUG
########################################


# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = os.environ.get('EMAIL_PORT', 587)
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', True)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', )
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'EXCEPTION_HANDLER': 'apps.api.exceptions.exceptions',
}

SESSION_COOKIE_HTTPONLY = True

# REST_FRAMEWORK = {
#     'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
#     'PAGE_SIZE': 20
# }
