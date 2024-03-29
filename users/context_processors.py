# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def brand_context(request):
    """"""

    if hasattr(request, "user"):
        if not request.user.is_authenticated:
            return {}

        brand = request.user.brand
        if brand is not None:
            return {
                 'brand_color': brand.color,
                 'brand_logo': brand.logo.url
            }
        return {}

    return {}


def current_status(request):
    """return value is disbursement or collection"""

    if hasattr(request, "user"):
        if not request.user.is_authenticated:
            return {}

        current_status = request.user.get_status(request)
        other_status = 'disbursement' if current_status == 'collection' else 'collection'
        return {
            'current_status': current_status,
            'other_status': other_status
        }

    return {}
