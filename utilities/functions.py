# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from environ import ImproperlyConfigured

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
