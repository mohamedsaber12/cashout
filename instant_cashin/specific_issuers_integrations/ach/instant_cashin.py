# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import decimal

import json
import logging
import uuid

from requests.exceptions import ConnectionError, HTTPError
import requests

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from rest_framework import status
from rest_framework.response import Response

from disbursement.models import BankTransaction, RemainingAmounts
from disbursement.utils import (BANK_TRX_BEING_PROCESSED,
                                BANK_TRX_IS_SUCCESSFUL_1,
                                BANK_TRX_IS_SUCCESSFUL_2, BANK_TRX_RECEIVED,
                                EXTERNAL_ERROR_MSG,
                                INSTANT_TRX_BEING_PROCESSED,
                                INSTANT_TRX_IS_ACCEPTED,
                                INSTANT_TRX_IS_REJECTED, INSTANT_TRX_RECEIVED,
                                INTERNAL_ERROR_MSG, TRX_REJECTED_BY_BANK_CODES,
                                TRX_RETURNED_BY_BANK_CODES)
from utilities.ssl_certificate import SSLCertificate

from ...api.serializers import (BankTransactionResponseModelSerializer,
                                InstantTransactionResponseModelSerializer)
from ...models import AbstractBaseIssuer, InstantTransaction
from ...utils import get_from_env

ACH_SEND_TRX_LOGGER = logging.getLogger('ach_send_transaction.log')
ACH_GET_TRX_STATUS_LOGGER = logging.getLogger("ach_get_transaction_status")
from instant_cashin.specific_issuers_integrations.aman.instant_cashin import UUIDEncoder



class BankTransactionsChannel:
    """
    Handles disbursement for bank wallets/cards
    """

    @staticmethod
    def create_new_trx_out_of_passed_one(bank_trx_obj):
        new_transaction_dict = {
            'currency': bank_trx_obj.currency,
            'status': bank_trx_obj.status,
            'category_code': bank_trx_obj.category_code,
            'purpose': bank_trx_obj.purpose,
            'parent_transaction': bank_trx_obj.parent_transaction,
            'document': bank_trx_obj.document,
            'is_single_step': bank_trx_obj.is_single_step,
            'user_created': bank_trx_obj.user_created,
            'transaction_status_code': bank_trx_obj.transaction_status_code,
            'transaction_status_description': bank_trx_obj.transaction_status_description,
            'debtor_account': bank_trx_obj.debtor_account,
            'amount': bank_trx_obj.amount,
            'creditor_name': bank_trx_obj.creditor_name,
            'creditor_account_number': bank_trx_obj.creditor_account_number,
            'creditor_bank': bank_trx_obj.creditor_bank,
            'creditor_bank_branch': bank_trx_obj.creditor_bank_branch,
            'end_to_end': bank_trx_obj.end_to_end,
            'creditor_email': bank_trx_obj.creditor_email,
            'creditor_mobile_number': bank_trx_obj.creditor_mobile_number,
            'corporate_code': bank_trx_obj.corporate_code,
            'sender_id': bank_trx_obj.sender_id,
            'creditor_id': bank_trx_obj.creditor_id,
            'creditor_address_1': bank_trx_obj.creditor_address_1,
            'debtor_address_1': bank_trx_obj.debtor_address_1,
            'additional_info_1': bank_trx_obj.additional_info_1,
            'disbursed_date': bank_trx_obj.disbursed_date,
            'client_transaction_reference': bank_trx_obj.client_transaction_reference,
            "fees": bank_trx_obj.fees,
            "vat": bank_trx_obj.vat
        }
        return BankTransaction.objects.create(**new_transaction_dict)

    @staticmethod
    def get_corresponding_instant_trx_if_any(bank_trx_obj):
        """Return corresponding instant transaction if the bank trx is a bank wallet one"""
        if bank_trx_obj.end_to_end:
            try:
                return InstantTransaction.objects.get(uid=bank_trx_obj.end_to_end)
            except InstantTransaction.DoesNotExist:
                return False
        return False

    @staticmethod
    def accumulate_send_transaction_payload(trx_obj, amount_to_be_deducted=0):
        """
        Accumulates SendTransaction API request payload
        :param trx_obj: transaction object that saved after serializer passed validations
        :return: payload dictionary ready to be shipped to EBC
        """
        payload = dict()
        payload['TransactionId'] = str(trx_obj.transaction_id.hex)
        payload['MessageId'] = str(trx_obj.message_id.hex)
        payload['TransactionDateTime'] = trx_obj.created_at.strftime("%d/%m/%Y %H:%M:%S")
        payload['CategoryCode'] = trx_obj.category_code
        payload['TransactionPurpose'] = trx_obj.purpose
        payload['TransactionAmount'] = float(trx_obj.amount - decimal.Decimal(amount_to_be_deducted))
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
    def accumulate_get_transaction_status_payload(trx_obj):
        """
        Accumulates GetTransactionStatus API request payload
        :param trx_obj: transaction object that saved after serializer passed validations
        :return: payload dictionary ready to be shipped to EBC
        """
        payload = dict()
        payload['TransactionId'] = str(trx_obj.parent_transaction.transaction_id.hex)
        payload['MessageId'] = str(uuid.uuid4().hex)
        payload['CorporateCode'] = trx_obj.corporate_code

        json_payload = json.dumps(payload, separators=(",", ":"))
        payload['Signature'] = SSLCertificate.generate_signature(get_from_env('PRIVATE_KEY_NAME'), json_payload)

        return payload

    @staticmethod
    def post(url, payload, bank_trx_obj):
        """Handles POST requests to EBC using requests package"""
        log_header = "SEND ACH TRANSACTION TO EBC"
        ACH_SEND_TRX_LOGGER.debug(_(f"[request] [{log_header}] [{bank_trx_obj.user_created}] -- {payload}"))

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
            ACH_SEND_TRX_LOGGER.debug(
                    _(f"[response] [{log_header}] [{bank_trx_obj.user_created}] -- {response_log_message}")
            )

        raise ValidationError(_(response_log_message))

    @staticmethod
    def get(url, payload, bank_trx_obj):
        """Handles GET requests to EBC via requests package"""
        log_header = "get ach transaction status from EBC"
        ACH_GET_TRX_STATUS_LOGGER.debug(_(f"[request] [{log_header}] [{bank_trx_obj.user_created}] -- {payload}"))

        try:
            response = requests.get(
                    url + "?",
                    params={"request": json.dumps(payload, separators=(",", ":"))},
                    headers={'Content-Type': 'application/json'}
            )
            response_log_message = f"{response.json()}"
        except HTTPError as http_err:
            response_log_message = f"HTTP error occurred: {http_err}"
        except ConnectionError as connect_err:
            response_log_message = f"Connection establishment error: {connect_err}"
        except Exception as err:
            response_log_message = f"Other error occurred: {err}"
        else:
            return response
        finally:
            ACH_GET_TRX_STATUS_LOGGER.debug(
                    _(f"[response] [{log_header}] [{bank_trx_obj.user_created}] -- {response_log_message}")
            )

        raise ValidationError(_(response_log_message))

    @staticmethod
    def map_response_code_and_message(bank_trx_obj, instant_trx_obj, json_response):
        """Map EBC response code and message"""
        response_code = json_response.get("ResponseCode", status.HTTP_424_FAILED_DEPENDENCY)

        if instant_trx_obj:
            issuer = "orange" if instant_trx_obj.issuer_type == AbstractBaseIssuer.ORANGE else "bank_wallet"
        else:
            issuer = "bank_card"

        # 1. Transaction is validated and accepted by EBC, and or dispatched for being processed by the bank
        if response_code in ["8000", "8111"]:
            if response_code == "8000":
                bank_message = BANK_TRX_RECEIVED
                instant_message = INSTANT_TRX_RECEIVED
            else:
                bank_message = BANK_TRX_BEING_PROCESSED
                instant_message = INSTANT_TRX_BEING_PROCESSED

            bank_trx_obj.mark_pending(response_code, bank_message)
            instant_trx_obj.mark_pending(response_code, instant_message) if instant_trx_obj else None
            bank_trx_obj.user_created.root.\
                budget.update_disbursed_amount_and_current_balance(bank_trx_obj.amount, issuer)

        # 2. Transaction validation is rejected by EBC because of invalid bank swift code
        elif response_code == "8002":
            bank_trx_obj.mark_failed(response_code, _("Invalid bank swift code"))

        # 3. Transaction validation is rejected by EBC because of internal errors
        elif response_code in ["8001", "8003", "8004", "8005", "8006", "8007", "8008", "8011", "8888"]:
            bank_trx_obj.mark_failed(status.HTTP_500_INTERNAL_SERVER_ERROR, INTERNAL_ERROR_MSG)
        else:
            # 4. Transaction is failed due to unexpected response code for the send transaction api endpoint
            bank_trx_obj.mark_failed(status.HTTP_424_FAILED_DEPENDENCY, EXTERNAL_ERROR_MSG)

        # If the bank transaction isn't accepted and it is bank wallet/orange mark it as failed at the instant trx table
        if instant_trx_obj and response_code not in ["8000", "8111"]:
            instant_trx_obj.mark_failed("8888", INSTANT_TRX_IS_REJECTED)

        return bank_trx_obj, instant_trx_obj

    @staticmethod
    def update_bank_trx_status(bank_trx_obj, json_response):
        """Update bank transaction status after any GetTransactionStatus call to EBC"""
        response_code = json_response.get("TransactionStatusCode", "")
        response_description = json_response.get("TransactionStatusDescription", "")

        # 1. If the new status code is exact to the current transaction's status code return without updating
        if response_code == bank_trx_obj.transaction_status_code:
            return bank_trx_obj

        # 2. If the new status code is not in the expected status codes list ignore it and return without updating
        elif response_code not in ["8111", "8222", "8333"] + TRX_RETURNED_BY_BANK_CODES + TRX_REJECTED_BY_BANK_CODES:
            return bank_trx_obj

        # 3. Otherwise start creating new bank transaction with the new status code
        else:
            new_trx_obj = BankTransactionsChannel.create_new_trx_out_of_passed_one(bank_trx_obj)
            
             # send bank transaction callback notifications
            if response_code and response_description and bank_trx_obj.user_created.root.root.callback_url:
                callback_url = bank_trx_obj.user_created.root.root.callback_url
                req_body = BankTransactionResponseModelSerializer(bank_trx_obj)
                requests.post(callback_url, data=json.dumps(req_body.data, cls=UUIDEncoder))

            # 3.1) Transaction accepted by the bank
            if response_code == "8111":
                new_trx_obj.mark_pending(response_code, BANK_TRX_BEING_PROCESSED)
                instant_trx = BankTransactionsChannel.get_corresponding_instant_trx_if_any(new_trx_obj)
                instant_trx.mark_pending(response_code, INSTANT_TRX_BEING_PROCESSED) if instant_trx else None

            # 3.2) Transaction is accepted by the bank - first settlement or final settlement
            elif response_code in ["8222", "8333"]:
                bank_trx_message = BANK_TRX_IS_SUCCESSFUL_1 if response_code == "8222" else BANK_TRX_IS_SUCCESSFUL_2
                new_trx_obj.mark_successful(response_code, bank_trx_message)
                instant_trx = BankTransactionsChannel.get_corresponding_instant_trx_if_any(new_trx_obj)
                instant_trx.mark_successful("8222", INSTANT_TRX_IS_ACCEPTED) if instant_trx else None

            # 3.4) Handle bank reject and return cases
            elif response_code in TRX_REJECTED_BY_BANK_CODES + TRX_RETURNED_BY_BANK_CODES:
                # 3.4.1) Transaction is rejected by the bank
                if response_code in TRX_REJECTED_BY_BANK_CODES:
                    new_trx_obj.mark_rejected(response_code, response_description)

                # 3.4.2) Transaction is returned by the bank
                else:
                    new_trx_obj.mark_returned(response_code, response_description)

                instant_trx = BankTransactionsChannel.get_corresponding_instant_trx_if_any(new_trx_obj)
                instant_trx.mark_failed("8888", INSTANT_TRX_IS_REJECTED) if instant_trx else None
                new_trx_obj.user_created.root.budget.return_disbursed_amount_for_cancelled_trx(new_trx_obj.amount)

            return new_trx_obj

    @staticmethod
    def send_transaction(bank_trx_obj, instant_trx_obj):
        """Make a new send transaction request to EBC"""
            
        has_valid_response = True

        try:
            # UVA issue remaining money 
            # TODO Remove this code after all remining money is zero (UVA-Admin)
            amount_to_be_deducted = 0
            if bank_trx_obj.user_created.root.username == "UVA-Admin":
                remaining_amounts = RemainingAmounts.objects.filter(remaining_amount__gt=0)
                for remaining_amount_obj in remaining_amounts:
                    if remaining_amount_obj.mobile in bank_trx_obj.creditor_account_number:
                        if bank_trx_obj.amount - remaining_amount_obj.remaining_amount >= 1:
                            amount_to_be_deducted = remaining_amount_obj.remaining_amount
                            remaining_amount_obj.remaining_amount = decimal.Decimal(0)
                        else:
                            amount_to_be_deducted = bank_trx_obj.amount - 1
                            remaining_amount_obj.remaining_amount = remaining_amount_obj.remaining_amount - amount_to_be_deducted
                        remaining_amount_obj.save()



            payload = BankTransactionsChannel.accumulate_send_transaction_payload(bank_trx_obj, amount_to_be_deducted)
            response = BankTransactionsChannel.post(get_from_env("EBC_API_URL"), payload, bank_trx_obj)
        except (HTTPError, ConnectionError, Exception) as e:
            has_valid_response = False
            ACH_SEND_TRX_LOGGER.debug(_(f"[message] [ACH EXCEPTION] [{bank_trx_obj.user_created}] -- {e.args}"))
            bank_trx_obj.mark_failed(status.HTTP_424_FAILED_DEPENDENCY, EXTERNAL_ERROR_MSG)
            instant_trx_obj.mark_failed(status.HTTP_424_FAILED_DEPENDENCY, EXTERNAL_ERROR_MSG) if instant_trx_obj \
                else None

        if has_valid_response:
            bank_trx_obj, instant_trx_obj = BankTransactionsChannel. \
                map_response_code_and_message(bank_trx_obj, instant_trx_obj, json.loads(response.json()))

        if instant_trx_obj:
            return Response(InstantTransactionResponseModelSerializer(instant_trx_obj).data)
        else:
            return Response(BankTransactionResponseModelSerializer(bank_trx_obj).data)

    @staticmethod
    def get_transaction_status(bank_trx_obj):
        """Inquire about a bank transaction status"""
        try:
            payload = BankTransactionsChannel.accumulate_get_transaction_status_payload(bank_trx_obj)
            response = BankTransactionsChannel.get(get_from_env("EBC_API_URL"), payload, bank_trx_obj)
            new_bank_trx_obj = BankTransactionsChannel.update_bank_trx_status(bank_trx_obj, json.loads(response.json()))
            return Response(BankTransactionResponseModelSerializer(new_bank_trx_obj).data)
        except (HTTPError, ConnectionError, Exception) as e:
            ACH_GET_TRX_STATUS_LOGGER.debug(_(f"[message] [ACH EXCEPTION] [{bank_trx_obj.user_created}] -- {e.args}"))
            return Response(BankTransactionResponseModelSerializer(bank_trx_obj).data)
