# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from requests.exceptions import ConnectionError, HTTPError
import json
import logging
import requests

from django.utils.translation import ugettext as _


class CustomRequests:
    """
    Customize requests module
    """

    def __init__(self, use_custom_logging=False, log_file=None, request_obj=None):
        self.use_custom_logging = use_custom_logging
        self.log_file = log_file
        self.request_obj = request_obj
        self.resp_log_msg = ''

    def log_message(self, head, request, message):
        """Custom logging for http requests"""
        self.request_logger = logging.getLogger(self.log_file)
        self.request_logger.debug(_(f"{head} [{request.user}] -- {message}"))

    def post(self, url, payload, headers=dict(), sub_logging_head='', **kwargs):
        """Handles POST requests using requests package"""
        if headers.get('Content-Type', None) is None:
            headers.update({'Content-Type': 'application/json'})

        if self.use_custom_logging:
            self.log_message(f"[request] [{sub_logging_head}]", self.request_obj, f"{payload}, URL: {url}")

        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, **kwargs)
            response.raise_for_status()
            self.resp_log_msg = f"{response.json()}"
        except HTTPError as http_err:
            self.resp_log_msg = f"HTTP error occurred: {http_err}"
        except ConnectionError as connect_err:
            self.resp_log_msg = f"Connection establishment error: {connect_err}"
        except Exception as err:
            self.resp_log_msg = f"Other error occurred: {err}"
        else:
            return response
        finally:
            if self.use_custom_logging:
                self.log_message(f"[response] [{sub_logging_head}]", self.request_obj, self.resp_log_msg)
