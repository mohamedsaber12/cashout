# -*- coding: utf-8 -*-
from .server import *


ALLOWED_HOSTS += [
    'payouts-ci.paymobsolutions.com',
]

# Email Reporting
#ADMINS += [
 #   ('Omar Nawar', 'omarnawar@paymob.com'),
#]

# base url
BASE_URL = 'https://payouts-ci.paymobsolutions.com'
