# -*- coding: utf-8 -*-
from .server import *

CSRF_TRUSTED_ORIGINS = ['payouts-k8s.paymobsolutions.com']

ALLOWED_HOSTS += (
    '18.220.63.67',
    '127.0.0.1',
    'payouts-k8s.paymobsolutions.com'
)

# base url
BASE_URL = 'https://payouts-k8s.paymobsolutions.com'
