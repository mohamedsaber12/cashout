# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from requests.exceptions import ConnectionError, HTTPError
import copy
import json
import logging
import requests

from .logging import logging_message


class CustomRequests:
    """
    Customize requests module
    """

    def __init__(self, log_file, request_obj=''):
        self.request_logger = logging.getLogger(log_file)
        self.request_obj = request_obj

    def log_message(self, head, request_obj, message):
        """Custom logging for http requests"""
        logging_message(self.request_logger, head, request_obj, message)

    def refine_to_be_logged_payload(self, payload, sub_logging_head):
        """Remove pins from the to be logged payload if any"""
        payload_deepcopy = copy.deepcopy(payload)

        if sub_logging_head == 'VODAFONE BULK DISBURSEMENT':
            for senders_dictionary in payload_deepcopy['SENDERS']:
                senders_dictionary['PIN'] = 'xxxxxx'
        elif sub_logging_head == 'ETISALAT BULK DISBURSEMENT':
            payload_deepcopy['PIN'] = 'xxxxxx'
        return payload_deepcopy

    def post(self, url, payload, sub_logging_head, headers=dict(), **kwargs):
        """Handles POST requests using requests package"""
        if headers.get('Content-Type', None) is None:
            headers.update({'Content-Type': 'application/json'})

        refined_payload = self.refine_to_be_logged_payload(payload, sub_logging_head)
        self.log_message(
                head=f"[POST REQUEST - {sub_logging_head}]", request_obj=self.request_obj,
                message=f"URL: {url}\nHeaders: {headers}\nKwargs: {kwargs}\nPayload: {refined_payload}"
        )

        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False, **kwargs)
            response.raise_for_status()
            response_log_message = f"Response: {response.json()}"
        except HTTPError as http_err:
            response_log_message = f"HTTP error occurred: {http_err}"
        except ConnectionError as connect_err:
            response_log_message = f"Connection establishment error: {connect_err}"
        except Exception as err:
            response_log_message = f"Other error occurred: {err}"
        else:
            return response
        finally:
            self.log_message(f"[POST RESPONSE - {sub_logging_head}]", self.request_obj, response_log_message)
