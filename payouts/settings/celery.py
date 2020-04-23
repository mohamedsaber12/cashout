# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os

from celery import Celery, signals


# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'payouts.settings')

app = Celery('payouts')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# ToDo: Add custom logging to the running celery tasks
# @signals.setup_logging.connect
# def on_celery_setup_logging(**kwargs):
#     config = {
#         'version': 1,
#         'disable_existing_loggers': False,
#         "filters": {
#             "request_id": {
#                 "()": "log_request_id.filters.RequestIDFilter"
#             }
#         },
#         'formatters': {
#             'detail': {
#                 'format': "\n[%(asctime)s] name=%(name)s func_name=%(funcName)s message=%(message)s",
#                 # 'format': "\n%(asctime)s [request_id=%(funcName)s] %(message)s",
#                 'datefmt': "%d-%m-%Y %H:%M:%S",
#             }
#         },
#         'handlers': {
#             'celery': {
#                 'level': 'DEBUG',
#                 'filters': ['request_id'],
#                 'class': 'logging.FileHandler',
#                 'filename': 'temp_celery.log',
#                 'formatter': 'detail',
#             },
#         },
#         'loggers': {
#             'celery': {
#                 'handlers': ['celery'],
#                 'level': 'DEBUG',
#                 'propagate': False
#             },
#         },
#         'root': {
#             'handlers': ['celery'],
#             'level': 'DEBUG'
#         },
#     }
#
#     logging.config.dictConfig(config)
