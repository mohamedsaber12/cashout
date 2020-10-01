# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from requests.exceptions import ConnectionError, HTTPError
import json
import requests
import logging

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from rest_framework import status
from rest_framework.response import Response

from utilities.ssl_certificate import SSLCertificate

from ...utils import get_from_env


SEND_TRX_LOGGER = logging.getLogger('ach_send_transaction.log')
EXTERNAL_ERROR_MSG = _("Process stopped during an external error, can you try again or contact your support team.")
PENDING_CODES_LIST = ["8000", "8111"]


class BankTransactionsChannel:
    """
    """

    @staticmethod
    def accumulate_send_transaction_payload(trx_obj):
        """
        Accumulates SendTransaction API request payload
        :param trx_obj: transaction object that saved after serializer passed validations
        :return: payload dictionary ready to be shipped to EBC
        """
        payload = dict()
        payload['TransactionId'] = str(trx_obj.id.hex)
        payload['MessageId'] = str(trx_obj.message_id.hex)
        payload['TransactionDateTime'] = trx_obj.created_at.strftime("%d/%m/%Y %H:%M:%S")
        payload['CategoryCode'] = trx_obj.category_code
        payload['TransactionPurpose'] = trx_obj.purpose
        payload['TransactionAmount'] = float(trx_obj.amount)
        payload['Currency'] = trx_obj.currency
        payload['CorporateCode'] = trx_obj.corporate_code
        payload['DebtorAccount'] = trx_obj.debtor_account
        payload['CreditorName'] = trx_obj.creditor_name
        payload['CreditorAccountNumber'] = trx_obj.creditor_account_number
        payload['CreditorBank'] = trx_obj.creditor_bank
        payload['CreditorAddress1'] = trx_obj.creditor_address_1
        payload['DebtorAddress1'] = trx_obj.debtor_address_1

        json_payload = json.dumps(payload, separators=(",", ":"))
        payload['Signature'] = SSLCertificate.generate_signature(get_from_env('PRIVATE_KEY_NAME'), json_payload)

        return payload

    @staticmethod
    def post(url, payload):
        """Handles POST requests using requests package"""
        SEND_TRX_LOGGER.debug(_(f"Payload: {payload}"))

        try:
            response = requests.post(
                    url,
                    data=json.dumps(payload, separators=(",", ":")),
                    headers={'Content-Type': 'application/json'}
            )
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
            SEND_TRX_LOGGER.debug(_(f"{response_log_message}"))

        # raise ValidationError(_(response_log_message))

    @staticmethod
    def send_transaction(bank_trx_obj):
        """
        """
        try:
            payload = BankTransactionsChannel.accumulate_send_transaction_payload(bank_trx_obj)
            response = BankTransactionsChannel.post(get_from_env("EBC_API_URL"), payload)
            json_response = response.json()
            bank_trx_obj.transaction_status_description = json_response.get('ResponseCode', EXTERNAL_ERROR_MSG)
            bank_trx_obj.transaction_status_code = json_response.get('ResponseCode', '8888')

            if bank_trx_obj.transaction_status_code in PENDING_CODES_LIST:
                bank_trx_obj.mark_pending()
            else:
                bank_trx_obj.mark_failed()
            # output_serializer = ResponseBankTransactionSerializer(bank_trx_obj)
            return Response({
                "transaction_id": bank_trx_obj.id,
                "disbursement_status": bank_trx_obj.status,
                "status_code": bank_trx_obj.transaction_status_code,
                "disbursement_description": bank_trx_obj.transaction_status_description
            }, status=status.HTTP_201_CREATED)
        except (HTTPError, ConnectionError) as e:
            return Response(
                    {'message': EXTERNAL_ERROR_MSG},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
