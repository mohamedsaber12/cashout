# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import template

from ..utils import get_error_description_from_error_code

register = template.Library()


@register.filter
def code_description(code):
    """Map error code regarding corresponding description message"""

    return get_error_description_from_error_code(code)
