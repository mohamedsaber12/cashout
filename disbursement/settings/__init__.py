from __future__ import absolute_import

try:
    from .local import *
except ImportError:
    from .production import *

from .celery import app as celery_app

__all__ = ['celery_app']
