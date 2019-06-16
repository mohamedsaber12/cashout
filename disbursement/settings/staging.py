from .base import *

DEBUG = False

ALLOWED_HOSTS += (
    'payroll.paymobsolutions.com',
)

INSTALLED_APPS += (
    'django_extensions',
)

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': env.str('DB_NAME'),
        'USER': env.str('DB_USER'),
        'PASSWORD': env.str('DB_PASS'),
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

ADMINS = [('Amir Raouf', 'amirraouf@paymobsolutions.com'),
          ('karim abdelhakim', 'karimabdelhakim@paymobsolutions.com'),
          ]
# celery

CELERY_BROKER_URL = 'amqp://paymobsecure:(!~)qwe!~@localhost//'

# ssl

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# base url
BASE_URL = 'https://payroll.paymobsolutions.com'

# session expiration
SESSION_EXPIRE_SECONDS = 300
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_EXPIRE_AFTER_LAST_ACTIVITY = True
