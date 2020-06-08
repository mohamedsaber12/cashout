# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from requests.exceptions import ConnectionError, HTTPError
import json
import logging
import requests

from .logging import logging_message


class CustomRequests:
    """
    Customize requests module
    """

    def __init__(self, use_custom_logging=False, log_file=None, request_obj=None):
        self.use_custom_logging = use_custom_logging
        self.log_file = log_file
        self.request_obj = request_obj
        self.resp_log_msg = ''

    def log_message(self, head, request_obj, message):
        """Custom logging for http requests"""
        self.request_logger = logging.getLogger(self.log_file)
        logging_message(self.request_logger, head, request_obj, message)

    def post(self, url, payload, headers=dict(), sub_logging_head='', **kwargs):
        """Handles POST requests using requests package"""
        if headers.get('Content-Type', None) is None:
            headers.update({'Content-Type': 'application/json'})

        if self.use_custom_logging:
            self.log_message(
                    head=f"[POST REQUEST - {sub_logging_head}]", request_obj=self.request_obj,
                    message=f"URL: {url}\nHeaders: {headers}\nKwargs: {kwargs}\nPayload: {payload}"
            )

        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, **kwargs)
            response.raise_for_status()
            self.resp_log_msg = f"Response: {response.json()}"
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
                self.log_message(f"[POST RESPONSE - {sub_logging_head}]", self.request_obj, self.resp_log_msg)
