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
SERVER_EMAIL = 'noreply@paymob.com'
EMAIL_BACKEND = 'django_smtp_ssl.SSLEmailBackend'
EMAIL_HOST = 'email-smtp.us-east-1.amazonaws.com'
EMAIL_PORT = 465
EMAIL_HOST_USER = env.str('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env.str('EMAIL_HOST_PASSWORD')

# Email Reporting
ADMINS = [
    ('Mohamed Saber', 'mohamedsaber@paymob.com'),
    ('Mohamed Awad', 'mohamedawad@paymob.com'),
]

# SSL
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# SECURE_SSL_REDIRECT = True        # Handled by nginx

# Sessions and Cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Log request ID
LOG_REQUEST_ID_HEADER = "HTTP_X_REQUEST_ID"
GENERATE_REQUEST_ID_IF_NOT_IN_HEADER = True

# To enable request ID from Nginx add this format to nginx.conf
# log_format compo '$remote_addr [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" '
#                     '"$http_host" "$scheme" "$host" '
#                     '"$server_port" "$server_protocol" '
#                     '"$request_time" "$request_id" "$upstream_addr" "$upstream_response_time" '
#                     '"$upstream_connect_time" '
#                     '"$upstream_header_time" '
#                     '"$upstream_status" "$msec" "$pipe" "$connection_requests"';

# access_log  /var/log/nginx/access.log  compo;

# location {
#     proxy_set_header X-Request-Id $request_id;
# }

# Enable HTTP Strict Transport Security (HSTS)
# proxy_set_header X-Forwarded-Proto $scheme;  >>  Add to nginx configs
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF=True
