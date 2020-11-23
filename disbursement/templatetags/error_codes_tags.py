# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import template
from django.utils.translation import ugettext_lazy as _

from disbursement.utils import ERROR_CODES_MESSAGES

register = template.Library()


@register.filter
def code_description(code):
    """Map error code regarding corresponding description message"""

    if code:
        message = ERROR_CODES_MESSAGES.get(code)
        if message:
            return _(message)
        else:
            return 'Error, please contact your support team'
    else:
        return 'Error, please contact your support team'