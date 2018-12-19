"""
Django settings for disbursement project.

Generated by 'django-admin startproject' using Django 2.0.7.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import os

import environ
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

env = environ.Env()

BASE_DIR = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '_3yre1ofg7bw9c51u+gcnjh977=1f*+8r2zj-q(ainog2h&tb('

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 3rd party apps
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_expiring_authtoken',
    'bootstrap4',
    'django_celery_beat',
    'imagekit',


    # security
    'request_id',
    'django_otp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
    'two_factor',

    # apps
    'data',
    'users',
    'disb',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'users.middleware.EntitySetupCompletionMiddleWare',
    'users.middleware.CheckerTwoFactorAuthMiddleWare',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'disbursement.urls'

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
                'users.context_processors.brand_context'
            ],
        },
    },
]

WSGI_APPLICATION = 'disbursement.wsgi.application'

# Celery

CELERY_TIMEZONE = 'Africa/Cairo'

#Send results back as AMQP messages
CELERY_RESULT_BACKEND = 'rpc://'
CELERY_RESULT_PERSISTENT = False

CELERY_ACCEPT_CONTENT = ['json']

CELERY_BROKER_URL = 'amqp://paymobsecure:(!~)qwe!~@localhost//'

CELERY_TASK_SERIALIZER = 'json'

MAX_TASK_RETRIES = 10

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators
AUTH_USER_MODEL = 'users.User'
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


# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

LANGUAGES = (
    ('en', _('English')),
    ('ar', _('Arabic')),
)

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

# Static files (CSS, JavaScript, Images)
STATIC_PATH = os.path.join(BASE_DIR, 'static')

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'static_root')
STATIC_URL = '/static/'
LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'conf/locale'),
)
FILE_UPLOAD_PERMISSIONS = 0o644


OTP_LOGIN_URL = reverse_lazy('users:user_login_view')
# LOGIN_REDIRECT_URL = '/'
LOGIN_URL = 'users:user_login_view'
LOGIN_REDIRECT_URL = 'two_factor:setup'
# RestFramework
REST_FRAMEWORK = {
    'PAGE_SIZE': 10,
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
    ),
}

ADMIN_SITE_HEADER = "PayMob Administration"

LOGIN_EXEMPT_URLS = (
    r'^user/logout/$',
    r'^user/login/$',
    r'^password/reset/$',
    r'^change_password/(?P<user>[0-9A-Za-z]+)/$',
    r'^password/reset/done/$',
    r'^password/reset/(?P<uidb64>[0-9A-Za-z]+)/(?P<token>.+)/$',
    r'^password/done/$',
)


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    "filters": {
        "request_id": {
            "()": "request_id.logging.RequestIdFilter"
        }
    },
    'formatters': {
        'console': {
            'format': u'%(asctime)s - %(levelname)-5s [%(name)s] request_id=%(request_id)s %(message)s',
            'datefmt': '%d/%m/%Y %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['request_id'],
            'class': 'logging.StreamHandler',
            'formatter': 'console'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/debug.log',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
        'file_upload': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/upload.log',
        },
        'download_serve': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/download_serve.log',
        },
        'delete_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/deleted_files.log',
        },
        'unauthorized_file_delete': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/unauthorized_file_delete.log',
        },
        'upload_error': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/upload_error.log',
        },
        'disburse': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/disburse_logger.log',
        },
        'create_user': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/create_user.log',
        },
        'delete_user': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/deleted_users.log',
        },
        'delete_group':{
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/deleted_groups.log',
        },
        'login': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/login.log',
        },
        'logout': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/logout.log',
        },
        'failed_login': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/failed_login.log',
        },
        'setup_view': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/setup_view.log',
        },
        'delete_user_view':{
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/delete_user_view.log',
        },
        'levels_view': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/levels_view.log',
        },
        'root_create': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/roots_created.log',
        },
        'agent_create': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/agents_created.log',
        },
        'view_document': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/view_document.log',
        },
        'failed_disbursement_download': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/failed_disbursement_download.log',
        },
        
    },

    'loggers': {
        "": {
            "level": "DEBUG",
            "handlers": ["console"]
        },
        'django': {
            'handlers': ['file', 'mail_admins'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'upload': {
            'handlers': ['file_upload'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'download_serve': {
            'handlers': ['download_serve'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'deleted_files': {
            'handlers': ['delete_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'unauthorized_file_delete': {
            'handlers': ['unauthorized_file_delete'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'upload_error': {
            'handlers': ['upload_error'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'disburse': {
            'handlers': ['disburse'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'created_users': {
            'handlers': ['create_user'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'delete_users': {
            'handlers': ['delete_user'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'delete_groups':{
            'handlers': ['delete_group'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'login': {
            'handlers': ['login'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'logout': {
            'handlers': ['logout'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'login_failed': {
            'handlers': ['failed_login'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'setup_view': {
            'handlers': ['setup_view'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'delete_user_view':{
            'handlers': ['delete_user_view'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'levels_view':{
            'handlers': ['levels_view'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'root_create':{
            'handlers': ['root_create'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'agent_create':{
            'handlers': ['agent_create'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'view_document': {
            'handlers': ['view_document'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'failed_disbursement_download':{
            'handlers': ['failed_disbursement_download'],
            'level': 'DEBUG',
            'propagate': True,
        }
        
    },
}
