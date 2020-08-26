# -*- coding: utf-8 -*-
from .server import *


ALLOWED_HOSTS += [
    'payouts.paymobsolutions.com',
    '52.8.5.130',
    '172.30.1.74',
]

# Email Reporting
ADMINS += [
    ('Omar Nawar', 'omarnawar@paymobsolutions.com')
]

# base url
BASE_URL = 'https://payouts.paymobsolutions.com'
