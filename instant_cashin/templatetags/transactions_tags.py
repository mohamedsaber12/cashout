# -*- coding: utf-8 -*-
from django import template
from django.utils.translation import ugettext_lazy as _

from core.models import AbstractBaseStatus

from ..models import AbstractBaseIssuer
from disbursement.utils import get_transformed_transaction_status

register = template.Library()


@register.filter
def issuer_type(issuer_value):
    """Transform transaction issuer key to into its corresponding informative string"""
    if issuer_value:
        if issuer_value == AbstractBaseIssuer.VODAFONE:
            return _("Vodafone")
        elif issuer_value == AbstractBaseIssuer.ETISALAT:
            return _("Etisalat")
        elif issuer_value == AbstractBaseIssuer.ORANGE:
            return _("Orange")
        elif issuer_value == AbstractBaseIssuer.BANK_WALLET:
            return _("Bank Wallet")
        elif issuer_value == AbstractBaseIssuer.AMAN:
            return _("Aman")
    else:
        return None


@register.filter
def status(status_value):
    """Transform transaction status key to into its corresponding informative string"""

    return get_transformed_transaction_status(status_value)
