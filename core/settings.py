import os
import logging
import tempfile
import atexit

from kubernetes import config
from base64 import b64decode
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from str2bool import str2bool
from dataclasses import dataclass
from urllib.parse import urlparse
from yaml import safe_load

from .utils import load_file_from_s3, load_file, generate_kid, cleanup

load_dotenv(override=True if os.environ.get('DEBUG') is None else False)

DEBUG = str2bool(os.environ.get('DEBUG'))
if DEBUG is None:
    DEBUG = True

print(f'# APP MODE -> {'DEVELOPMENT' if DEBUG else "PRODUCTION"}')

if not DEBUG:
    import sentry_sdk

    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        traces_sample_rate=1.0,  # Set to 1.0 to capture 100% of transactions for performance monitoring
        profiles_sample_rate=1.0,  # Set profiles_sample_rate to 1.0 to profile 100%
    )

logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)

ALGOLIA = {
    'APPLICATION_ID': os.environ.get('ALGOLIA_APP_ID'),
    'API_KEY': os.environ.get('ALGOLIA_API_KEY'),
}

BASE_DIR = Path(__file__).resolve().parent.parent

FIELD_ENCRYPTION_KEY = os.environ.get('FIELD_ENCRYPTION_KEY', '')


@dataclass
class Env:
    debug = DEBUG

    nyu_client_id = os.getenv('NYU_CLIENT_ID')
    nyu_client_secret = os.getenv('NYU_CLIENT_SECRET')
    nyu_openid_meta = os.getenv('NYU_META_URL')

    github_client_id = os.getenv('GITHUB_CLIENT_ID')
    github_client_secret = os.getenv('GITHUB_CLIENT_SECRET')
    github_token = os.getenv('GITHUB_TOKEN')

    mailgun_api_key = os.getenv('MAILGUN_API_KEY')
    mailgun_sender_domain = os.getenv('MAILGUN_SENDER_DOMAIN')
    mailgun_sender_email = os.getenv('MAILGUN_SENDER_EMAIL')

    rabbitmq_url = os.getenv('MQ_URL')

    cf_storage_url = os.getenv('CF_STORAGE_URL')
    cf_access_key = os.getenv('CF_ACCESS_KEY')
    cf_secret_key = os.getenv('CF_SECRET_KEY')

    aws_access_key = os.getenv('AWS_ACCESS_KEY')
    aws_secret_key = os.getenv('AWS_SECRET_KEY')
    kubeconfig_obj_path = os.getenv('KUBECONFIG_OBJECT_PATH')

    k8s_url = ''
    k8s_ws_url = ''
    k8s_config_dict = {}
    k8s_api_client = None
    k8s_aio_client = None
    k8s_auth = {
        'client_key': tempfile.NamedTemporaryFile(delete=False),
        'client_cert': tempfile.NamedTemporaryFile(delete=False),
        'ca_cert': tempfile.NamedTemporaryFile(delete=False),
    }

    registry_domain = os.getenv('REGISTRY_DOMAIN')
    registry_key_obj_path = os.getenv('REGISTRY_KEY_OBJECT_PATH')
    registry_signing_key = ''
    registry_kid = ''
    registry_webhook_secret = os.getenv('REGISTRY_WEBHOOK_SECRET')

    container_apps_domain = os.getenv('CONTAINER_APPS_DOMAIN')

    def __post_init__(self):
        kubeconfig_path = os.path.join(BASE_DIR, 'data/kubeconfig.yaml')
        if os.path.exists(kubeconfig_path):
            kubeconfig = load_file(kubeconfig_path, 'r')
        else:
            kubeconfig = load_file_from_s3(self.kubeconfig_obj_path, self.aws_access_key, self.aws_secret_key)

        if kubeconfig:
            kube_config = safe_load(kubeconfig)
            self.k8s_config_dict = kube_config

            url = urlparse(self.k8s_url)
            self.k8s_ws_url = 'ws://' if url.scheme == 'http' else 'wss://' + url.netloc + url.path
            self.k8s_api_client = config.new_client_from_config_dict(kube_config)
            print('# Initialized k8s client')

            current_context = kube_config['current-context']
            context = next(ctx for ctx in kube_config['contexts'] if ctx['name'] == current_context)
            user = next(usr for usr in kube_config['users'] if usr['name'] == context['context']['user'])
            user = user['user']

            if 'client-certificate-data' in user:  # For cert based auth
                # Write the certificate data to temp files
                self.k8s_auth['client_key'].write(b64decode(user['client-key-data']))
                self.k8s_auth['client_cert'].write(b64decode(user['client-certificate-data']))
                self.k8s_auth['ca_cert'].write(
                    b64decode(kube_config['clusters'][0]['cluster']['certificate-authority-data']))

                self.k8s_auth['client_key'].flush()
                self.k8s_auth['client_cert'].flush()
                self.k8s_auth['ca_cert'].flush()

                atexit.register(cleanup)

            if 'token' in user:  # For token based auth
                self.k8s_auth['token'] = user['token']

        else:
            print('# kubeconfig not found. k8s client not initialized')

        registry_signing_key_path = os.path.join(BASE_DIR, 'data/registry.key')
        if os.path.exists(registry_signing_key_path):
            self.registry_signing_key = load_file(registry_signing_key_path, 'rb')
        else:
            self.registry_signing_key = load_file_from_s3(self.registry_key_obj_path, self.aws_access_key,
                                                          self.aws_secret_key)

        if self.registry_signing_key:
            self.registry_kid = generate_kid(self.registry_signing_key, 'RSA')
            print('# Generated keyid from registry signing key')


env = Env()

SECRET_KEY = os.environ.get('SECRET_KEY')

SITE_URL = os.environ.get('SITE_URL')

USE_X_FORWARDED_HOST = str2bool(os.environ.get('USE_X_FORWARDED_HOST', 'False'))
USE_X_FORWARDED_PORT = str2bool(os.environ.get('USE_X_FORWARDED_PORT', 'False'))
USE_X_FORWARDED_PROTO = str2bool(os.environ.get('USE_X_FORWARDED_PROTO', 'False'))

ALLOWED_HOSTS = ['osiriscloud.io', 'staging.osiriscloud.io', 'localhost'] if not DEBUG else ['*']

CSRF_TRUSTED_ORIGINS = ['https://osiriscloud.io', 'https://staging.osiriscloud.io']
if DEBUG:
    CSRF_TRUSTED_ORIGINS += ['http://localhost:8000', 'https://localhost:8000']

with open('version.txt', 'r') as f:
    VER = f.read().strip()

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
    "django_seed",
    'drf_spectacular',
    'django_api_gen',
    'encrypted_model_fields',
    "main",
    "oidc_provider",
    "apps.api",
    "apps.infra",
    "apps.oauth",
    "apps.users",
    "apps.admin_console",
]

# Client facing apps
OC_APPS = [
    "apps.dashboard",
    "apps.container_registry",
    "apps.container_apps",
    "apps.secret_store",
]

INSTALLED_APPS += OC_APPS

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
    "oidc_provider.middleware.SessionManagementMiddleware",
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

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True

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
                "main.context_processor.version",
            ],
        },
    },
]

DATABASE_CONNECTION_POOLING = False

if not DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASS'),
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT'),
            'CONN_MAX_AGE': 300,
            'CONN_HEALTH_CHECKS': True,
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
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
TIME_ZONE = "America/New_York"
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

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

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
CELERY_TIMEZONE = 'EST'
CELERY_TASK_ALWAYS_EAGER = DEBUG  # Setting this to True will run tasks synchronously and block the main thread

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'apps.api.auth.AccessTokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'apps.api.auth.AccessTokenOrIsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'EXCEPTION_HANDLER': 'apps.api.exceptions.exception_processor',
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'osiris-app-cache',
    }
}

OIDC_LOGIN_URL = '/login/nyu'
OIDC_IDTOKEN_INCLUDE_CLAIMS = True
OIDC_EXTRA_SCOPE_CLAIMS = 'apps.oauth.provider.OsirisScopeClaims'
OIDC_SESSION_MANAGEMENT_ENABLE = True
OIDC_TEMPLATES = {
    'authorize': 'apps/oauth/authorize.html',
    'error': 'oidc_provider/error.html'
}
