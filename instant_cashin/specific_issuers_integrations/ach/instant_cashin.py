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

from ...api.serializers import BankTransactionResponseModelSerializer, InstantTransactionResponseModelSerializer
from ...utils import get_from_env


ACH_SEND_TRX_LOGGER = logging.getLogger('ach_send_transaction.log')


INTERNAL_ERROR_MSG = _("Process stopped during an internal error, can you try again or contact your support team.")
EXTERNAL_ERROR_MSG = _("Process stopped during an external error, can you try again or contact your support team.")
TRX_RECEIVED = _("Transaction is received and validated successfully, dispatched for being processed by the bank")
TRX_BEING_PROCESSED = _("Transaction is received by the bank and being processed now")


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
    def post(url, payload, bank_trx_obj):
        """Handles POST requests using requests package"""
        ACH_SEND_TRX_LOGGER.debug(_(f"[POST REQUEST]\n{bank_trx_obj.user_created} - {payload}"))

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
            ACH_SEND_TRX_LOGGER.debug(_(f"[POST RESPONSE]\n{bank_trx_obj.user_created} - {response_log_message}"))

        raise ValidationError(_(response_log_message))

    @staticmethod
    def map_response_code_and_message(bank_trx_obj, instant_trx_obj, json_response):
        """Map EBC response code and message"""
        response_code = json_response.get('ResponseCode', status.HTTP_424_FAILED_DEPENDENCY)

        if response_code == "8000":
            # ToDo: Update custom budget if pending/ and cancel it if failed
            bank_trx_obj.transaction_status_code = response_code
            bank_trx_obj.transaction_status_description = TRX_RECEIVED
            bank_trx_obj.mark_pending()
            instant_trx_obj.mark_pending() if instant_trx_obj else None
        elif response_code == "8111":
            bank_trx_obj.transaction_status_code = response_code
            bank_trx_obj.transaction_status_description = TRX_BEING_PROCESSED
            bank_trx_obj.mark_pending()
            instant_trx_obj.mark_pending() if instant_trx_obj else None
        elif response_code == "8002":
            bank_trx_obj.transaction_status_code = response_code
            bank_trx_obj.transaction_status_description = _("Invalid bank code")
            bank_trx_obj.mark_failed()
        elif response_code == "8011":
            bank_trx_obj.transaction_status_code = response_code
            bank_trx_obj.transaction_status_description = _("Invalid bank transaction type")
            bank_trx_obj.mark_failed()
        elif response_code in ["8001", "8003", "8004", "8005", "8006", "8007", "8008", "8888"]:
            bank_trx_obj.transaction_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            bank_trx_obj.transaction_status_description = INTERNAL_ERROR_MSG
            bank_trx_obj.mark_failed()
        else:
            bank_trx_obj.transaction_status_code = status.HTTP_424_FAILED_DEPENDENCY
            bank_trx_obj.transaction_status_description = EXTERNAL_ERROR_MSG
            bank_trx_obj.mark_failed()

        if instant_trx_obj and response_code not in ["8000", "8111"]:
            instant_trx_obj.mark_failed(status.HTTP_500_INTERNAL_SERVER_ERROR, EXTERNAL_ERROR_MSG)

        return bank_trx_obj, instant_trx_obj

    @staticmethod
    def send_transaction(bank_trx_obj, instant_trx_obj):
        """
        Make a new send transaction request to EBC
        """
        try:
            payload = BankTransactionsChannel.accumulate_send_transaction_payload(bank_trx_obj)
            response = BankTransactionsChannel.post(get_from_env("EBC_API_URL"), payload, bank_trx_obj)
            bank_trx_obj, instant_trx_obj = BankTransactionsChannel.\
                map_response_code_and_message(bank_trx_obj, instant_trx_obj, json.loads(response.json()))
            if instant_trx_obj:
                return Response(InstantTransactionResponseModelSerializer(instant_trx_obj).data)
            else:
                return Response(BankTransactionResponseModelSerializer(bank_trx_obj).data)
        except (HTTPError, ConnectionError, ValidationError, Exception) as e:
            ACH_SEND_TRX_LOGGER.debug(_(f"[EXCEPTION]\n{bank_trx_obj.user_created} - {e.args}"))
            if instant_trx_obj:
                instant_trx_obj.mark_failed(status.HTTP_500_INTERNAL_SERVER_ERROR, EXTERNAL_ERROR_MSG)
                return Response(InstantTransactionResponseModelSerializer(instant_trx_obj).data)
            else:
                bank_trx_obj.mark_failed()
                return Response(BankTransactionResponseModelSerializer(bank_trx_obj).data)
