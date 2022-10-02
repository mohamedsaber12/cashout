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
from ...models import InstantTransaction
from ...utils import get_from_env

ONE_LINK_ACCESS_TOKEN_LOGGER = logging.getLogger('one_link_access_token_requests')
ONE_LINK_FETCH_TITLE_LOGGER = logging.getLogger('one_link_fetch_title_requests')
ONE_LINK_PUSH_TRANSACTIONS_LOGGER = logging.getLogger('one_link_push_transaction_requests')


class OneLinkTransactionsChannel:
    """
    Handles disbursement for wallet, bank wallet and bank account/cards in pakistan
    """

    @staticmethod
    def accumulate_push_transaction_payload(trx_obj, fetch_title_response_obj):
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
        payload['PosEntryMode'] = get_from_env('POS_ENTRY_MODE')
        payload['SenderName'] = get_from_env('SENDER_NAME')
        payload['SenderIBAN'] = get_from_env('SENDER_IBAN_OR_MOBILE_NUMBER')
        payload['ToBankIMD'] = trx_obj.creditor_bank_imd
        payload['AccountNumberTo'] = trx_obj.anon_recipient

        return payload

    @staticmethod
    def accumulate_fetch_payload(trx_obj):
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
        payload['ToBankIMD'] = trx_obj.creditor_bank_imd
        payload['AccountNumberTo'] = trx_obj.anon_recipient

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

        payload = OneLinkTransactionsChannel.accumulate_fetch_payload(instant_trx_obj)

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
            _(f"[request] [{log_header}] [{instant_trx_obj.from_user}] [uid:- {instant_trx_obj.uid}] -- {payload}")
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
                _(f"[response] [{log_header}] [{instant_trx_obj.from_user}] [uid:- {instant_trx_obj.uid}] -- {response_log_message}")
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
            payload = OneLinkTransactionsChannel.accumulate_push_transaction_payload(
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
                _(f"[request] [{log_header}] [{instant_trx_obj.from_user}] [uid:- {instant_trx_obj.uid}] -- {payload}")
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
                    _(f"[response] [{log_header}] [{instant_trx_obj.from_user}] [uid:- {instant_trx_obj.uid}] -- {response_log_message}")
                )

            raise ValidationError(_(response_log_message))
        else:
            response_code = fetch_title_response_obj['ResponseCode']
            instant_trx_obj.mark_failed(
                    response_code , ONE_LINK_ERROR_CODES_MESSAGES[response_code])

    @staticmethod
    def map_response_code_and_message(instant_trx_obj, json_response):
        """Map One Link response code and message"""

        response_code = json_response.get("ResponseCode", status.HTTP_424_FAILED_DEPENDENCY)
        response_detail = ONE_LINK_ERROR_CODES_MESSAGES[str(response_code)]
        issuer = instant_trx_obj.issuer_type
        # 1. Transaction is validated and accepted by EBC, and or dispatched for being processed by the bank
        if response_code in ["00"]:
            balance_before = instant_trx_obj.from_user.root.budget.get_current_balance()
            balance_after = instant_trx_obj.from_user.root. \
                budget.update_disbursed_amount_and_current_balance(instant_trx_obj.amount, issuer)
            instant_trx_obj.balance_before = balance_before
            instant_trx_obj.balance_after = balance_after
            ONE_LINK_PUSH_TRANSACTIONS_LOGGER.debug(
                f"[message] balance before {balance_before} balance after {balance_after}")
            instant_trx_obj.save()
            ONE_LINK_PUSH_TRANSACTIONS_LOGGER.debug(
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
    def send_transaction(instant_trx_obj):
        """Make a new send transaction request to One Link"""

        has_valid_response = True

        try:
            response = OneLinkTransactionsChannel.post(get_from_env("ONE_LINK_IBFT_PUSH_URL"), instant_trx_obj)
            if response == None:
                has_valid_response = False
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
        if instant_trx_obj.issuer_type == InstantTransaction.BANK_CARD:
            return Response(BankTransactionResponseModelSerializer(instant_trx_obj).data)

        return Response(InstantTransactionResponseModelSerializer(instant_trx_obj).data)
