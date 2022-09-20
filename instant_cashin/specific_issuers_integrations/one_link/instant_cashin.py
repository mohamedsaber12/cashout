# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import decimal

import json
import logging
import uuid

from requests.exceptions import ConnectionError, HTTPError
import requests

from datetime import datetime
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
                                TRX_RETURNED_BY_BANK_CODES,
                                ONE_LINK_ERROR_CODES_MESSAGES)
from utilities.ssl_certificate import SSLCertificate

from ...api.serializers import (BankTransactionResponseModelSerializer,
                                InstantTransactionResponseModelSerializer)
from ...models import AbstractBaseIssuer, InstantTransaction
from ...utils import get_from_env

ACH_SEND_TRX_LOGGER = logging.getLogger('ach_send_transaction.log')
ONE_LINK_ACCESS_TOKEN_LOGGER = logging.getLogger('one_link_access_token_requests.log')
ONE_LINK_FETCH_TITLE_LOGGER = logging.getLogger('one_link_fetch_title_requests.log')
ONE_LINK_PUSH_TRANSACTIONS_LOGGER = logging.getLogger('one_link_push_transaction_requests.log')
ACH_GET_TRX_STATUS_LOGGER = logging.getLogger("ach_get_transaction_status")
CALLBACK_REQUESTS_LOGGER = logging.getLogger("callback_requests")


class OneLinkTransactionsChannel:
    """
    Handles disbursement for bank account/cards in pakistan
    """

    @staticmethod
    def create_new_trx_out_of_passed_one(bank_trx_obj):
        new_transaction_dict = {
            'currency'                      : bank_trx_obj.currency,
            'status'                        : bank_trx_obj.status,
            'category_code'                 : bank_trx_obj.category_code,
            'purpose'                       : bank_trx_obj.purpose,
            'parent_transaction'            : bank_trx_obj.parent_transaction,
            'document'                      : bank_trx_obj.document,
            'is_single_step'                : bank_trx_obj.is_single_step,
            'user_created'                  : bank_trx_obj.user_created,
            'transaction_status_code'       : bank_trx_obj.transaction_status_code,
            'transaction_status_description': bank_trx_obj.transaction_status_description,
            'debtor_account'                : bank_trx_obj.debtor_account,
            'amount'                        : bank_trx_obj.amount,
            'creditor_name'                 : bank_trx_obj.creditor_name,
            'creditor_account_number'       : bank_trx_obj.creditor_account_number,
            'creditor_bank'                 : bank_trx_obj.creditor_bank,
            'creditor_bank_branch'          : bank_trx_obj.creditor_bank_branch,
            'end_to_end'                    : bank_trx_obj.end_to_end,
            'creditor_email'                : bank_trx_obj.creditor_email,
            'creditor_mobile_number'        : bank_trx_obj.creditor_mobile_number,
            'corporate_code'                : bank_trx_obj.corporate_code,
            'sender_id'                     : bank_trx_obj.sender_id,
            'creditor_id'                   : bank_trx_obj.creditor_id,
            'creditor_address_1'            : bank_trx_obj.creditor_address_1,
            'debtor_address_1'              : bank_trx_obj.debtor_address_1,
            'additional_info_1'             : bank_trx_obj.additional_info_1,
            'disbursed_date'                : bank_trx_obj.disbursed_date,
            'client_transaction_reference'  : bank_trx_obj.client_transaction_reference,
            "fees"                          : bank_trx_obj.fees,
            "vat"                           : bank_trx_obj.vat,
            "balance_before"                : bank_trx_obj.balance_before,
            "balance_after"                 : bank_trx_obj.balance_after
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
    def accumulate_send_transaction_payload_for_bank(trx_obj, fetch_title_response_obj):
        """
        Accumulates SendTransaction API request payload
        :param trx_obj: transaction object that saved after serializer passed validations
        :return: payload dictionary ready to be shipped to One Link
        """
        payload = dict()
        payload['TransactionAmount'] = trx_obj.amount
        payload['Date'] = datetime.now().strftime("%m%d")
        payload['Time'] = datetime.now().strftime("%H%M%S")
        payload['TransmissionDateAndTime'] = f"{payload['Date']}{payload['Time']}"
        payload['STAN'] = trx_obj.stan
        payload['RRN'] = trx_obj.rrn
        payload['MerchantType'] = get_from_env('MERCHANT_TYPE')
        payload['AuthorizationIdentificationResponse'] = fetch_title_response_obj['AuthorizationIdentificationResponse']
        payload['CardAcceptorTerminalId'] = get_from_env('CARD_ACCEPTOR_TERMINAL_ID')
        payload['CardAcceptorIdCode'] = get_from_env('CARD_ACCEPTOR_ID_CODE')
        payload['CardAcceptorNameLocation'] = {
            "Location"  : get_from_env('CARD_ACCEPTOR_NAME_LOCATION_LOCATION'),
            "City"      : get_from_env('CARD_ACCEPTOR_NAME_LOCATION_CITY'),
            "State"     : get_from_env('CARD_ACCEPTOR_NAME_LOCATION_STATE'),
            "ZipCode"   : get_from_env('CARD_ACCEPTOR_NAME_LOCATION_ZIP_CODE'),
            "AgentName" : get_from_env('CARD_ACCEPTOR_NAME_LOCATION_AGENT_NAME'),
            "AgentCity" : get_from_env('CARD_ACCEPTOR_NAME_LOCATION_AGENT_CITY'),
            "ADCLiteral": get_from_env('CARD_ACCEPTOR_NAME_LOCATION_ADC_LITERAL'),
            "BankName"  : get_from_env('CARD_ACCEPTOR_NAME_LOCATION_BANK_NAME'),
            "Country"   : get_from_env('CARD_ACCEPTOR_NAME_LOCATION_COUNTRY')
        }
        payload['CurrencyCodeTransaction'] = get_from_env('CURRENCY_CODE_TRANSACTION')
        payload['FromBankIMD'] = get_from_env('FROM_BANK_IMD')
        payload['AccountNumberFrom'] = get_from_env('ACCOUNT_NUMBER_FROM')
        payload['ToBankIMD'] = trx_obj.creditor_bank
        payload['AccountNumberTo'] = trx_obj.anon_recipient
        payload['PosEntryMode'] = get_from_env('POS_ENTRY_MODE')
        payload['SenderName'] = get_from_env('SENDER_NAME')
        payload['SenderIBAN'] = get_from_env('SENDER_IBAN_OR_MOBILE_NUMBER')

        return payload

    @staticmethod
    def accumulate_fetch_payload_for_bank(trx_obj):
        """
        Accumulates fetch title API request payload
        :param trx_obj: transaction object that saved after serializer passed validations
        :return: payload dictionary ready to be shipped to One Link
        """
        payload = dict()
        payload['Date'] = datetime.now().strftime("%m%d")
        payload['Time'] = datetime.now().strftime("%H%M%S")
        payload['TransmissionDateAndTime'] = f"{payload['Date']}{payload['Time']}"
        payload['TransactionAmount'] = trx_obj.amount
        payload['STAN'] = trx_obj.stan
        payload['MerchantType'] = get_from_env('MERCHANT_TYPE')
        payload['FromBankIMD'] = get_from_env('FROM_BANK_IMD')
        payload['RRN'] = trx_obj.rrn
        payload['CardAcceptorTerminalId'] = get_from_env('CARD_ACCEPTOR_TERMINAL_ID')
        payload['CardAcceptorIdCode'] = get_from_env('CARD_ACCEPTOR_ID_CODE')
        payload['CardAcceptorNameLocation'] = {
            "Location": get_from_env('CARD_ACCEPTOR_NAME_LOCATION_LOCATION'),
            "City": get_from_env('CARD_ACCEPTOR_NAME_LOCATION_CITY'),
            "State": get_from_env('CARD_ACCEPTOR_NAME_LOCATION_STATE'),
            "ZipCode": get_from_env('CARD_ACCEPTOR_NAME_LOCATION_ZIP_CODE'),
            "AgentName": get_from_env('CARD_ACCEPTOR_NAME_LOCATION_AGENT_NAME'),
            "AgentCity": get_from_env('CARD_ACCEPTOR_NAME_LOCATION_AGENT_CITY'),
            "ADCLiteral": get_from_env('CARD_ACCEPTOR_NAME_LOCATION_ADC_LITERAL'),
            "BankName": get_from_env('CARD_ACCEPTOR_NAME_LOCATION_BANK_NAME'),
            "Country": get_from_env('CARD_ACCEPTOR_NAME_LOCATION_COUNTRY')
        }
        payload['CurrencyCodeTransaction'] = get_from_env('CURRENCY_CODE_TRANSACTION')
        payload['AccountNumberFrom'] = get_from_env('ACCOUNT_NUMBER_FROM')
        payload['ToBankIMD'] = trx_obj.creditor_bank
        payload['AccountNumberTo'] = trx_obj.anon_recipient

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
    def get_access_token():
        """Handles POST requests to One Link to get access token"""

        log_header = "SEND TOKEN REQUEST TO ONE LINK"

        one_link_token_url = get_from_env('ONE_LINK_API_TOKEN_URL')
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        request_body = {
            "client_id": get_from_env('ONE_LINK_CLIENT_ID'),
            "client_secret": get_from_env('ONE_LINK_CLIENT_SECRET'),
            "username": get_from_env('ONE_LINK_USERNAME'),
            "password": get_from_env('ONE_LINK_PASSWORD'),
        }
        request_body_for_logging = {
            "client_id"     : "XXXXX",
            "client_secret" : "XXXXX",
            "username"      : "XXXXX",
            "password"      : "XXXXX",
        }
        ONE_LINK_ACCESS_TOKEN_LOGGER.debug(
            _(f"[request] [{log_header}] -- {request_body_for_logging}")
        )
        try:
            response = requests.post(
                one_link_token_url, data=request_body, headers=headers
            )
            response_log_message = f"Response: {response.json()}"
        except HTTPError as http_err:
            response_log_message = f"HTTP error occurred: {http_err}"
        except ConnectionError as connect_err:
            response_log_message = f"Connection establishment error: {connect_err}"
        except Exception as err:
            response_log_message = f"Other error occurred: {err}"
        else:
            return response.json()['access_token']
        finally:
            ONE_LINK_ACCESS_TOKEN_LOGGER.debug(
                _(f"[response] [{log_header}] -- {response_log_message}")
            )

        raise ValidationError(_(response_log_message))

    @staticmethod
    def add_leading_zeros_to_amount(amount):
        length_of_amount = len(str(amount))

        # add leading zeros to make amount length equal to 12
        for i in range(0, 12 - length_of_amount):
            amount = f"0{amount}"

        # remove . sign and zeros after it ex => (000000100.00 will be 000000000100)
        amount = f"000{amount[:-3]}"
        return amount

    @staticmethod
    def fetch_title(instant_trx_obj, current_access_token):
        """Handles POST requests to One Link to fetch title of transaction"""

        log_header = "SEND FETCH TITLE REQUEST TO ONE LINK"

        payload = OneLinkTransactionsChannel.accumulate_fetch_payload_for_bank(instant_trx_obj)

        payload['TransactionAmount'] = OneLinkTransactionsChannel.add_leading_zeros_to_amount(
            payload['TransactionAmount'])

        one_link_fetch_title_url = get_from_env('ONE_LINK_FETCH_TITLE_URL')

        headers = {
            'Content-Type'   : 'application/json',
            'Accept'         : 'application/json',
            'Authorization'  : f"Bearer {current_access_token}",
            'X-IBM-Client-Id': get_from_env('ONE_LINK_CLIENT_ID'),
        }
        ONE_LINK_FETCH_TITLE_LOGGER.debug(
            _(f"[request] [{log_header}] -- {payload}")
        )
        try:
            response = requests.post(
                one_link_fetch_title_url, json=payload, headers=headers
            )
            response_log_message = f"Response: {response.json()}"
        except HTTPError as http_err:
            response_log_message = f"HTTP error occurred: {http_err}"
        except ConnectionError as connect_err:
            response_log_message = f"Connection establishment error: {connect_err}"
        except Exception as err:
            response_log_message = f"Other error occurred: {err}"
        else:
            return response.json()
        finally:
            ONE_LINK_FETCH_TITLE_LOGGER.debug(
                _(f"[response] [{log_header}] -- {response_log_message}")
            )

        raise ValidationError(_(response_log_message))

    @staticmethod
    def post(url, instant_trx_obj):
        """Handles POST requests to One Link using requests package"""

        # get access token
        current_access_token = OneLinkTransactionsChannel.get_access_token()

        # send fetch title request
        fetch_title_response_obj = OneLinkTransactionsChannel.fetch_title(instant_trx_obj, current_access_token)

        if fetch_title_response_obj['ResponseCode'] == "00":
            # this means fetch request success
            payload = OneLinkTransactionsChannel.accumulate_send_transaction_payload_for_bank(
                    instant_trx_obj, fetch_title_response_obj)

            payload['TransactionAmount'] = OneLinkTransactionsChannel.add_leading_zeros_to_amount(
                    payload['TransactionAmount'])

            log_header = "SEND Bank TRANSACTION TO ONE LINK"

            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f"Bearer {current_access_token}",
                'X-IBM-Client-Id': get_from_env('ONE_LINK_CLIENT_ID'),
            }

            ONE_LINK_PUSH_TRANSACTIONS_LOGGER.debug(
                _(f"[request] [{log_header}] -- [{instant_trx_obj.from_user}] -- {payload}")
            )
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=30
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
                ONE_LINK_PUSH_TRANSACTIONS_LOGGER.debug(
                    _(f"[response] [{log_header}] [{instant_trx_obj.from_user}] -- {response_log_message}")
                )

            raise ValidationError(_(response_log_message))
        else:
            response_code = fetch_title_response_obj['ResponseCode']
            instant_trx_obj.mark_failed(
                    response_code , ONE_LINK_ERROR_CODES_MESSAGES[response_code])

    @staticmethod
    def get(url, payload, bank_trx_obj):
        """Handles GET requests to EBC via requests package"""
        log_header = "get ach transaction status from EBC"
        ACH_GET_TRX_STATUS_LOGGER.debug(_(f"[request] [{log_header}] [{bank_trx_obj.user_created}] -- {payload}"))

        try:
            response = requests.get(
                    url + "?",
                    params={"request": json.dumps(payload, separators=(",", ":"))},
                    headers={'Content-Type': 'application/json'},
                    timeout=10
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
    def map_response_code_and_message(instant_trx_obj, json_response):
        """Map One Link response code and message"""

        response_code = json_response.get("ResponseCode", status.HTTP_424_FAILED_DEPENDENCY)
        response_detail = ONE_LINK_ERROR_CODES_MESSAGES[str(response_code)]
        issuer = "bank_card"
        # 1. Transaction is validated and accepted by EBC, and or dispatched for being processed by the bank
        if response_code in ["00"]:
            balance_before = instant_trx_obj.from_user.root.budget.get_current_balance()
            balance_after = instant_trx_obj.from_user.root. \
                budget.update_disbursed_amount_and_current_balance(instant_trx_obj.amount, issuer)
            instant_trx_obj.balance_before = balance_before
            instant_trx_obj.balance_after = balance_after
            ACH_SEND_TRX_LOGGER.debug(
                f"[message] balance before {balance_before} balance after {balance_after}")
            instant_trx_obj.save()
            ACH_SEND_TRX_LOGGER.debug(
                f"[message] obj balance before {instant_trx_obj.balance_before} obj balance after {instant_trx_obj.balance_after}")

            instant_trx_obj.mark_successful(response_code, response_detail)
        else:
            instant_trx_obj.mark_failed(response_code, response_detail)

        # # 2. Transaction validation is rejected by EBC because of invalid bank swift code
        # elif response_code=="8002":
        #     balance_before = balance_after = bank_trx_obj.user_created.root.budget.get_current_balance()
        #     bank_trx_obj.balance_before = balance_before
        #     bank_trx_obj.balance_after = balance_after
        #     bank_trx_obj.save()
        #     bank_trx_obj.mark_failed(response_code, _("Invalid bank swift code"))
        #
        # # 3. Transaction validation is rejected by EBC because of internal errors
        # elif response_code in ["8001", "8003", "8004", "8005", "8006", "8007", "8008", "8011", "8888"]:
        #     balance_before = balance_after = bank_trx_obj.user_created.root.budget.get_current_balance()
        #     bank_trx_obj.balance_before = balance_before
        #     bank_trx_obj.balance_after = balance_after
        #     bank_trx_obj.save()
        #     bank_trx_obj.mark_failed(status.HTTP_500_INTERNAL_SERVER_ERROR, INTERNAL_ERROR_MSG)
        # else:
        #     # 4. Transaction is failed due to unexpected response code for the send transaction api endpoint
        #     balance_before = balance_after = bank_trx_obj.user_created.root.budget.get_current_balance()
        #     bank_trx_obj.balance_before = balance_before
        #     bank_trx_obj.balance_after = balance_after
        #     bank_trx_obj.save()
        #     bank_trx_obj.mark_failed(status.HTTP_424_FAILED_DEPENDENCY, EXTERNAL_ERROR_MSG)
        #
        # # If the bank transaction isn't accepted and it is bank wallet/orange mark it as failed at the instant trx table
        # if instant_trx_obj and response_code not in ["8000", "8111"]:
        #     balance_before = balance_after = bank_trx_obj.user_created.root.budget.get_current_balance()
        #     instant_trx_obj.balance_before = balance_before
        #     instant_trx_obj.balance_after = balance_after
        #     instant_trx_obj.save()
        #     instant_trx_obj.mark_failed("8888", INSTANT_TRX_IS_REJECTED)

        return instant_trx_obj

    @staticmethod
    def update_bank_trx_status(bank_trx_obj, json_response):
        """Update bank transaction status after any GetTransactionStatus call to EBC"""
        response_code = json_response.get("TransactionStatusCode", "")
        response_description = json_response.get("TransactionStatusDescription", "")

        # 1. If the new status code is exact to the current transaction's status code return without updating
        if response_code==bank_trx_obj.transaction_status_code:
            return bank_trx_obj

        # 2. If the new status code is not in the expected status codes list ignore it and return without updating
        elif response_code not in ["8111", "8222", "8333"] + TRX_RETURNED_BY_BANK_CODES + TRX_REJECTED_BY_BANK_CODES:
            return bank_trx_obj

        # 3. Otherwise start creating new bank transaction with the new status code
        else:
            new_trx_obj = BankTransactionsChannel.create_new_trx_out_of_passed_one(bank_trx_obj)

            # 3.1) Transaction accepted by the bank
            if response_code=="8111":
                new_trx_obj.mark_pending(response_code, BANK_TRX_BEING_PROCESSED)
                instant_trx = BankTransactionsChannel.get_corresponding_instant_trx_if_any(new_trx_obj)
                instant_trx.mark_pending(response_code, INSTANT_TRX_BEING_PROCESSED) if instant_trx else None

            # 3.2) Transaction is accepted by the bank - first settlement or final settlement
            elif response_code in ["8222", "8333"]:
                bank_trx_message = BANK_TRX_IS_SUCCESSFUL_1 if response_code=="8222" else BANK_TRX_IS_SUCCESSFUL_2
                new_trx_obj.mark_successful(response_code, bank_trx_message)
                instant_trx = BankTransactionsChannel.get_corresponding_instant_trx_if_any(new_trx_obj)
                instant_trx.mark_successful(response_code, INSTANT_TRX_IS_ACCEPTED) if instant_trx else None

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
                balance_before = new_trx_obj.user_created.root.budget.get_current_balance()
                balance_after = new_trx_obj.user_created.root.budget.return_disbursed_amount_for_cancelled_trx(
                    new_trx_obj.amount)
                new_trx_obj.balance_before = balance_before
                new_trx_obj.balance_after = balance_after
                new_trx_obj.save()
                if instant_trx:
                    instant_trx.balance_before = balance_before
                    instant_trx.balance_after = balance_after
                    instant_trx.save()

            # send bank transaction callback notifications
            if response_code and response_description and bank_trx_obj.user_created.root.root.callback_url:
                callback_url = bank_trx_obj.user_created.root.callback_url
                callback_payload = {
                    'transaction_id'              : str(new_trx_obj.parent_transaction.transaction_id),
                    'issuer'                      : 'bank_card',
                    'amount'                      : str(new_trx_obj.amount),
                    'bank_card_number'            : str(new_trx_obj.creditor_account_number),
                    'full_name'                   : str(new_trx_obj.creditor_name),
                    'bank_code'                   : str(new_trx_obj.creditor_bank),
                    'bank_transaction_type'       : str(bank_trx_obj.get_transaction_type),
                    'disbursement_status'         : str(new_trx_obj.status_choice_verbose),
                    'status_code'                 : str(new_trx_obj.transaction_status_code),
                    'status_description'          : str(new_trx_obj.transaction_status_description),
                    'client_transaction_reference': str(new_trx_obj.client_transaction_reference),
                    'created_at'                  : new_trx_obj.parent_transaction.created_at.strftime(
                        "%Y-%m-%d %H:%M:%S.%f"),
                    'updated_at'                  : new_trx_obj.updated_at.strftime("%Y-%m-%d %H:%M:%S.%f")
                }
                response = requests.post(callback_url, json=callback_payload)

                log_header = "send callback request to ==> "
                CALLBACK_REQUESTS_LOGGER.debug(
                        _(f"[callback request] [{log_header}] [{callback_url}] [{bank_trx_obj.user_created}] -- {callback_payload}")
                )
                log_header = "received callback response from ==> "
                CALLBACK_REQUESTS_LOGGER.debug(
                        _(f"[callback response] [{log_header}] [{callback_url}] [{bank_trx_obj.user_created}] -- {response.json()}")
                )

            return new_trx_obj

    @staticmethod
    def send_transaction(instant_trx_obj):
        """Make a new send transaction request to One Link"""

        has_valid_response = True

        try:
            response = OneLinkTransactionsChannel.post(get_from_env("ONE_LINK_IBFT_PUSH_URL"), instant_trx_obj)
        except (HTTPError, ConnectionError, Exception) as e:
            has_valid_response = False
            ONE_LINK_PUSH_TRANSACTIONS_LOGGER.debug(_(f"[message] [ONE LINK EXCEPTION] [{instant_trx_obj.from_user}] -- {e}"))
            balance_before = balance_after = instant_trx_obj.from_user.root.budget.get_current_balance()
            instant_trx_obj.balance_before = balance_before
            instant_trx_obj.balance_after = balance_after
            instant_trx_obj.save()
            instant_trx_obj.mark_failed(status.HTTP_424_FAILED_DEPENDENCY, EXTERNAL_ERROR_MSG)

        if has_valid_response:
            instant_trx_obj = OneLinkTransactionsChannel. \
                map_response_code_and_message(instant_trx_obj, response.json())

        return Response(BankTransactionResponseModelSerializer(instant_trx_obj).data)

    @staticmethod
    def get_transaction_status(bank_trx_obj):
        """Inquire about a bank transaction status"""
        try:
            payload = BankTransactionsChannel.accumulate_get_transaction_status_payload(bank_trx_obj)
            response = BankTransactionsChannel.get(get_from_env("EBC_API_URL"), payload, bank_trx_obj)
            new_bank_trx_obj = BankTransactionsChannel.update_bank_trx_status(bank_trx_obj, json.loads(response.json()))
            return Response(BankTransactionResponseModelSerializer(new_bank_trx_obj).data)
        except (HTTPError, ConnectionError, Exception) as e:
            ACH_GET_TRX_STATUS_LOGGER.debug(
                    _(f"[message] [ACH EXCEPTION] [{bank_trx_obj.user_created}] [bank_trx_id ==> {str(bank_trx_obj.transatcion_id)}] -- {e.args}")
            )
            return Response(BankTransactionResponseModelSerializer(bank_trx_obj).data)
