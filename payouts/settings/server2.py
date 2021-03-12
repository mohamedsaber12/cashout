from .base import *
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': env.str('DB_NAME'),
        'USER': env.str('DB_USER'),
        'PASSWORD': env.str('DB_PASSWORD'),
        'HOST': env.str('DB_HOST'),
        'PORT': '5432',
    },
}
DEBUG = False
#SERVER_EMAIL = 'confirmrequest@paymobsolutions.com'
# EMAIL_BACKEND = 'django_smtp_ssl.SSLEmailBackend'
#EMAIL_HOST = 'email-smtp.eu-west-1.amazonaws.com'
#EMAIL_PORT = 465
#EMAIL_HOST_USER = env.str('EMAIL_HOST_USER')
#EMAIL_HOST_PASSWORD = env.str('EMAIL_HOST_PASSWORD')
# Mailing Configs
#BASE_URL = 'https://payouts-ci.paymobsolutions.com'
BASE_URL = 'http://localhost:8000'
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'payouts-ci.paymobsolutions.com']
if DEBUG:
    # SERVER_EMAIL = 'django.core.mail.backends.console.EmailBackend'
    # SERVER_EMAIL = 'django.core.mail.backends.smtp.EmailBackend'
    # EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
