# -*- coding: utf-8 -*-
from .server import *


ALLOWED_HOSTS += (
    'payouts.paymobsolutions.com',
    '54.91.163.127',
)

# Email Reporting
ADMINS += [
    ('Omar Nawar', 'omarnawar@paymobsolutions.com')
]

# base url
BASE_URL = 'https://payouts.paymobsolutions.com'
