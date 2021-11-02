# -*- coding: utf-8 -*-
from .server import *

CSRF_TRUSTED_ORIGINS = ['payouts-ci.paymobsolutions.com']

ALLOWED_HOSTS += (
    '18.220.63.67',
    'payouts-ci.paymobsolutions.com',
    '127.0.0.1',
    '*'
)

# base url
#BASE_URL = 'https://payouts-ci.paymobsolutions.com'
