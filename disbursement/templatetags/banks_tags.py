# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import template
from django.utils.translation import ugettext_lazy as _

from disbursement.utils import BANK_CODES

register = template.Library()


@register.filter
def bank_name(code):
    """Map bank name regarding corresponding bank code"""

    if code:
        for record in BANK_CODES:
            if code == record['code']:
                return _(record['name'])
    else:
        return ''


@register.filter
def transaction_type(transaction_obj):
    """Map transaction type used at doc upload regarding the trx details"""

    if transaction_obj.purpose == 'SALA':
        return _('Salary')
    elif transaction_obj.purpose == 'CCRD':
        return _('Credit card')
    elif transaction_obj.category_code == 'PCRD':
        return _('Prepaid card')
    else:
        return _('Cash transfer')
