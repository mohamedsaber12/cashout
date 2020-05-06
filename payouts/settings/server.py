# -*- coding: utf-8 -*-
from .base import *


DEBUG = False

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': env.str('DB_NAME'),
        'USER': env.str('DB_USER'),
        'PASSWORD': env.str('DB_PASSWORD'),
        'HOST': 'localhost',
        'PORT': '',
        'CONN_MAX_AGE': 600,
    }
}

# Email
SERVER_EMAIL = 'confirmrequest@paymobsolutions.com'
EMAIL_BACKEND = 'django_smtp_ssl.SSLEmailBackend'
EMAIL_HOST = 'email-smtp.eu-west-1.amazonaws.com'
EMAIL_PORT = 465
EMAIL_HOST_USER = env.str('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env.str('EMAIL_HOST_PASSWORD')

# Email Reporting
ADMINS = [
    ('Mohamed Mamdouh', 'mohamedmamdouh@paymobsolutions.com')
]

# SSL
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# SECURE_SSL_REDIRECT = True        # Handled by nginx

# Sessions and Cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# session expiration
SESSION_EXPIRE_SECONDS = 300
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_EXPIRE_AFTER_LAST_ACTIVITY = True

# Enable HTTP Strict Transport Security (HSTS)
# proxy_set_header X-Forwarded-Proto $scheme;  >>  Add to nginx configs
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF=True
