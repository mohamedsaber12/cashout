# -*- coding: utf-8 -*-
from .server2 import *


ALLOWED_HOSTS += [
    'payouts.paymobsolutions.com',
    'vodafonepayouts.paymob.com',
    '52.8.5.130',
    '172.30.1.74',
]

# Email Reporting
ADMINS += [
    ('Omar Nawar', 'omarnawar@paymob.com'),
]

# base url
BASE_URL = 'https://payouts.paymobsolutions.com'

