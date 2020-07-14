# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from io import BytesIO

from django.http import HttpResponse
from django.template.loader import get_template

from environ import ImproperlyConfigured
from xhtml2pdf import pisa

from payouts.utils import get_dot_env


def get_value_from_env(key):
    """
    :param key: Key that will be used to retrieve its corresponding value
    This function will get the corresponding value of a key from the .env file
    """
    environment_vars_dict = get_dot_env()

    if not environment_vars_dict.str(key):
        raise ImproperlyConfigured(f"{key} does not exist at your .env file")

    return environment_vars_dict.str(key)


def render_to_pdf(src_template, context_dict={}):
    """
    Takes HTML template and renders it as pdf
    :param src_template: html template to be rendered as pdf
    :param context_dict: dictionary passed to the html file
    """

    template = get_template(src_template)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)

    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')

    return None
