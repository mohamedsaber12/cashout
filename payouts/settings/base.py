import datetime
import os

import environ
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from ..custom_logging import CUSTOM_LOGGING

"""
Django settings for payouts project.

Generated by 'django-admin startproject' using Django 2.0.7.
"""

BASE_DIR = os.path.dirname(
        os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
        )
)

env = environ.Env()
env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['0.0.0.0','127.0.0.1', 'localhost', "172.31.8.189", "172.31.23.159", "75.2.116.217", "99.83.194.66"]

# Application definition
THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_expiring_authtoken',
    'phonenumber_field',
    'django_celery_beat',
    'imagekit',
    'django_extensions',
    'django.contrib.admindocs',
    'log_viewer',
    'simple_history',
    'rangefilter',
    'django_admin_multiple_choice_list_filter',
]

SECURITY_THIRD_PARTY_APPS = [
    'django_otp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
    'two_factor',
    'axes',
    'oauth2_provider',
    'user_sessions',
]

USER_DEFINED_APPS = [
    'users',
    'data',
    'disbursement',
    'payment',
    'instant_cashin',
    'utilities',
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
INSTALLED_APPS += THIRD_PARTY_APPS
INSTALLED_APPS += SECURITY_THIRD_PARTY_APPS
INSTALLED_APPS += USER_DEFINED_APPS

MIDDLEWARE = [
    'utilities.middleware.SetRemoteAddrFromForwardedFor',

    # https://github.com/dabapps/django-log-request-id
    'log_request_id.middleware.RequestIDMiddleware',

    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',

    # Third party user sessions middleware
    'user_sessions.middleware.SessionMiddleware',

    # If you use SessionAuthenticationMiddleware, be sure it appears before OAuth2TokenMiddleware.
    # SessionAuthenticationMiddleware is NOT required for using django-oauth-toolkit.
    # 'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'oauth2_provider.middleware.OAuth2TokenMiddleware',

    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'users.middleware.EntitySetupCompletionMiddleWare',
    'users.middleware.AdministrativeTwoFactorAuthMiddleWare',
    'users.middleware.AgentAndSuperAgentForAdminMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'csp.middleware.CSPMiddleware',

    # Must be the last middleware in the list
    'axes.middleware.AxesMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    'instant_cashin.middleware.ip_whitelist.FilterIPMiddleware'

    # ToDo: Request/Response Time Delta Middleware
]

# disable AdministrativeTwoFactorAuthMiddleWare on local
if env.str('ENVIRONMENT') == "local":
    MIDDLEWARE.remove("users.middleware.AdministrativeTwoFactorAuthMiddleWare")


AUTHENTICATION_BACKENDS = [
    # OAuth2.0 Provider
    'oauth2_provider.backends.OAuth2Backend',

    # AxesBackend should be the first backend in the AUTHENTICATION_BACKENDS list.
    'axes.backends.AxesBackend',

    # Django ModelBackend is the default authentication backend.
    'django.contrib.auth.backends.ModelBackend',
]

ROOT_URLCONF = 'payouts.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'users.context_processors.brand_context',
                'users.context_processors.current_status'
            ],
        },
    },
]

WSGI_APPLICATION = 'payouts.wsgi.application'

# Celery configs
# Send results back as AMQP messages
CELERY_RESULT_BACKEND = 'rpc://'
CELERY_BROKER_URL = env.str('CELERY_BROKER_URL')
CELERY_RESULT_ACCEPT_CONTENT = ['json']
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_PERSISTENT = False
MAX_TASK_RETRIES = 10
CELERY_TIMEZONE = 'Africa/Cairo'

#The validity period of the link Reset password
PASSWORD_RESET_TIMEOUT=env.int("PASSWORD_RESET_TIMEOUT")

# Password validation
CUSTOM_PASSWORD_VALIDATOR = [
    {
        'NAME': 'users.validators.NumberValidator',
        'OPTIONS': {
            'min_digits': 2,
        }
    },
    {
        'NAME': 'users.validators.UppercaseValidator',
        'OPTIONS': {
            'min_chars': 2,
        }
    },
    {
        'NAME': 'users.validators.LowercaseValidator',
        'OPTIONS': {
            'min_chars': 2,
        }
    },
    {
        'NAME': 'users.validators.SymbolValidator',
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_PASSWORD_VALIDATORS += CUSTOM_PASSWORD_VALIDATOR

# Configure our custom user model to be the default auto user model
AUTH_USER_MODEL = 'users.User'

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/
LANGUAGE_CODE = 'en-us'

LANGUAGES = (
    ('en', _('English')),
    ('ar', _('Arabic')),
)

TIME_ZONE = 'Africa/Cairo'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# MKDocs Configs
DOCS_DIR = env.str('MKDOCS_ROOT')
DOCS_STATIC_NAMESPACE = os.path.basename(DOCS_DIR)

# Static files (CSS, JavaScript, Images)
STATIC_PATH = os.path.join(BASE_DIR, 'static')

MEDIA_ROOT = env.str('MEDIA_ROOT')
MEDIA_URL = '/media/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
    env.str('DOCS_STATIC_ROOT')
]
STATIC_ROOT = env.str('STATIC_ROOT')
STATIC_URL = '/static/'

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'conf/locale'),
)
FILE_UPLOAD_PERMISSIONS = 0o644

# Rest-Framework
REST_FRAMEWORK = {
    'PAGE_SIZE': 50,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'EXCEPTION_HANDLER': 'instant_cashin.api.exceptions.custom_exception_handler',
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # OAuth2.0 Provider
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
        'rest_framework_expiring_authtoken.authentication.ExpiringTokenAuthentication',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'user': '5/min',
    },
}

# Login Configurations
OTP_LOGIN_URL = reverse_lazy('users:user_login_view')
# LOGIN_REDIRECT_URL = '/'
LOGIN_URL = 'users:user_login_view'
LOGIN_REDIRECT_URL = 'two_factor:setup'

LOGIN_EXEMPT_URLS = (
    r'^user/logout/$',
    r'^user/login/$',
    r'^password/reset/$',
    r'^forgot-password/$',
    r'^change_password/(?P<user>[0-9A-Za-z]+)/$',
    r'^password/reset/done/$',
    r'^password/reset/(?P<uidb64>[0-9A-Za-z]+)/(?P<token>.+)/$',
    r'^password/done/$',
    r'^api*',
    r'^docs/*'
)
EXPIRING_TOKEN_LIFESPAN = datetime.timedelta(minutes=60)

LOGGING = CUSTOM_LOGGING

# Axes Custom Configurations
AXES_COOLOFF_TIME = datetime.timedelta(minutes=15)
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True
AXES_FAILURE_LIMIT = 5
AXES_ENABLE_ADMIN = True
AXES_VERBOSE = False
AXES_LOCKOUT_TEMPLATE = 'data/login.html'
AXES_LOGGER = 'axes_watcher'

# OAuth2 provider configs
OAUTH2_PROVIDER = {
    # this is the list of available scopes
    'OAUTH2_VALIDATOR_CLASS': 'utilities.validators.AxesOAuth2Validator',
    'SCOPES': {
        'read': 'Read scope',
        'write': 'Write scope',
        'groups': 'Group scope'
    },
    'ACCESS_TOKEN_EXPIRE_SECONDS': 60*60,
}

# Session 3rd party package
SESSION_ENGINE = 'user_sessions.backends.db'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 60 * 60
GEOIP_PATH = os.path.join(MEDIA_ROOT, 'GeoLite2-City.mmdb')
SILENCED_SYSTEM_CHECKS = ['admin.E410']

# Admin Panel Typos
ADMIN_SITE_HEADER = 'Payouts Admin Panel'
ADMIN_SITE_TITLE = 'Paymob'
ADMIN_INDEX_TITLE = 'Payouts Administration'

# Timeout dictionary
TIMEOUT_CONSTANTS = {
    'CENTRAL_UIG': 33
}


# log viewer settings

LOG_VIEWER_FILES = ['wallet_api.log', 'custom_budgets.log']
LOG_VIEWER_FILES_PATTERN = '*.log'
LOG_VIEWER_FILES_DIR = os.path.join(BASE_DIR, 'logs')
LOG_VIEWER_MAX_READ_LINES = 1000  # total log lines will be read
LOG_VIEWER_PAGE_LENGTH = 25       # total log lines per-page
LOG_VIEWER_PATTERNS = [']OFNI[', ']GUBED[', ']GNINRAW[', ']RORRE[', ']LACITIRC[']


SIMPLE_HISTORY_REVERT_DISABLED=True

BANK_WALLET_AND_ORNAGE_ISSUER = env.str('BANK_WALLET_AND_ORNAGE_ISSUER', "ACH")
ETISALAT_ISSUER = env.str('ETISALAT_ISSUER', "ETISALAT")

# RATELIMIT SETTINGS
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'


CACHES = {
    'default':{
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'dataflair_cache',
    }
}

#   Enable HSTS
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_PRELOAD = True


SECRET_KEY = env.str('SECRET_KEY')


## Sentry

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="https://87c556fc87c1467b83a09d06b3c09244@o1332627.ingest.sentry.io/6597349",
    integrations=[
        DjangoIntegration(),
    ],

    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,

    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True
)


VODAFONE_BALANCE_SUPER_AGENT_NUMBER=env.str('VODAFONE_BALANCE_SUPER_AGENT_NUMBER', "")
VODAFONE_BALANCE_SUPER_AGENT_NUMBER_PIN=env.str('VODAFONE_BALANCE_SUPER_AGENT_NUMBER_PIN', "")
VODAFONE_BALANCE_SUPER_ADMIN=env.str('VODAFONE_BALANCE_SUPER_ADMIN', "")

# Configuring CSP headers
CSP_DEFAULT_SRC = (
    "'self'", "maxcdn.bootstrapcdn.com",
    "cdnjs.cloudflare.com/ajax/libs/bootbox.js/4.4.0/bootbox.min.js",
    "cdnjs.cloudflare.com/ajax/libs/jszip/3.1.3/jszip.min.js",
    "ajax.googleapis.com/ajax/libs/jquery/1.12.0/jquery.min.js",
    "cdnjs.cloudflare.com/ajax/libs/highlight.js/10.5.0/styles/github.min.css",
    "cdnjs.cloudflare.com/ajax/libs/highlight.js/10.5.0/highlight.min.js",
    "cdnjs.cloudflare.com/ajax/libs/highlight.js/10.5.0/languages/rust.min.js",
    "cdnjs.cloudflare.com/ajax/libs/highlight.js/10.5.0/languages/yaml.min.js",
    "fonts.googleapis.com", "fonts.gstatic.com", "unpkg.com",
    "ajax.googleapis.com/ajax/libs/jquery", "'unsafe-inline'",
)
CSP_IMG_SRC = (
    "'self'", "data:", "user-images.githubusercontent.com",
)
CSP_OBJECT_SRC = (
    "'none'",
)
CSP_BASE_URI = (
    "'none'",
)
ADMIN_RANGEFILTER_NONCE_ENABLED = False
# add x-xss-protection header
SECURE_BROWSER_XSS_FILTER = True



# SSO 

IDMS_BASE_URL = env.str('IDMS_BASE_URL')
IDMS_CLIENT_ID = env.str('IDMS_CLIENT_ID')
IDMS_REDIRECT_URL = env.str('IDMS_REDIRECT_URL')
IDMS_CLIENT_SECRET = env.str('IDMS_CLIENT_SECRET')
IDMS_SSO_UID = env.str('IDMS_SSO_UID')