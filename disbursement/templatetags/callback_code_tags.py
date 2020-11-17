# -*- coding: utf-8 -*-

import re

from django import template
from django.utils.translation import ugettext_lazy as _

register = template.Library()


RESPONSE_CODES = (
    (re.compile('403'), _('Internal system error')),
    (re.compile('404'), _('Internal system error')),
    (re.compile('406'), _('User input incorrect data')),
    (re.compile('501'), _('Transaction time out')),
    (re.compile('583'), _('Transaction above 6000 EGP')),
    (re.compile('604'), _('Transaction below 5 EGP')),
    (re.compile('610'), _('User suspended')),
    (re.compile('615'), _('')),
    (re.compile('618'), _('')),
)


@register.filter
def device(value):
    """"""

    device = None
    for regex, name in RESPONSE_CODES:
        if regex.search(value):
            device = name
            break

    if device:
        return device

    return None
