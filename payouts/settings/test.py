"""
Django settings for sharing project. Base Settings

"""
from __future__ import absolute_import, unicode_literals

import os

from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from .base import *
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '+@j#)!v#a#hi4x4y&x@#y69&_co6#&mp=k+v6y1ghfewor3w&i'

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '52.52.224.160']

SESSION_EXPIRE_AT_BROWSER_CLOSE = True


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'bills_db_new',
        'USER': 'root',
        'PASSWORD': '018242',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,
        'TEST': {
            'NAME': 'bills_db_test',
        }
    }
}

# Application definition

AUTHENTICATION_BACKENDS = ['users.backends.BillsModelBackend']

MIDDLEWARE_CLASSES = [
    'user_sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'sharing.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates'), ],
        'APP_DIRS': False,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
            ],
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ]
        },
    },
]

WSGI_APPLICATION = 'sharing.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators
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

import logging
logging.disable(logging.CRITICAL)
# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

SITE_ID = 1

# Translation
LANGUAGE_CODE = 'en'
LANGUAGES = (
    ('en', _('English')),
    ('ar', _('Arabic')),
)

TIME_ZONE = 'Africa/Cairo'

USE_I18N = True

USE_L10N = True

USE_TZ = True

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

# Redirect
OTP_LOGIN_URL = reverse_lazy('two_factor:login')
LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/user/login/'
LOGOUT_REDIRECT_URL = LOGIN_URL

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
    )
}

ADMIN_SITE_HEADER = "PayMob Administration"

SESSION_ENGINE = 'user_sessions.backends.db'

# messages framework
from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

# time
timezone = 'Africa/Cairo'

# Mail settings
# ------------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_PORT = 1025
EMAIL_HOST = 'localhost'


# CACHING
# ------------------------------------------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': ''
    }
}

# TESTING
# ------------------------------------------------------------------------------
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
# Tell nose to measure coverage on the 'foo' and 'bar' apps
NOSE_ARGS = [
    '--with-coverage',
    '--cover-package=fines.models,fees.models,users,disbursement.api, disbursement.models,data.api, data.views, '
    'data.models, data.tasks,transactions.api, transactions.models,pcm,configuration.models',
    '--logging-clear-handlers',
    '--cover-html'
]
