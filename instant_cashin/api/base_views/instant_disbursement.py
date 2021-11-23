# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import logging
from users.models.base_user import User

import requests

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext as _
from django.utils import timezone

from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope, permissions
from rest_framework import status, views
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from disbursement.models import BankTransaction, VMTData
from payouts.settings import TIMEOUT_CONSTANTS
from utilities.logging import logging_message

from ...models import InstantTransaction
from ...specific_issuers_integrations import AmanChannel, BankTransactionsChannel
from ...utils import default_response_structure, get_digits, get_from_env
from ..mixins import IsInstantAPICheckerUser
from ..serializers import InstantDisbursementRequestSerializer, InstantTransactionResponseModelSerializer

INSTANT_CASHIN_SUCCESS_LOGGER = logging.getLogger("instant_cashin_success")
INSTANT_CASHIN_FAILURE_LOGGER = logging.getLogger("instant_cashin_failure")
INSTANT_CASHIN_REQUEST_LOGGER = logging.getLogger("instant_cashin_requests")

INTERNAL_ERROR_MSG = _("Process stopped during an internal error, can you try again or contact your support team")
EXTERNAL_ERROR_MSG = _("Process stopped during an external error, can you try again or contact your support team")
ORANGE_PENDING_MSG = _("Your transaction will be process the soonest, wait for a response at the next 24 hours")
BUDGET_EXCEEDED_MSG = _("Sorry, the amount to be disbursed exceeds you budget limit, please contact your support team")
TIMEOUT_ERROR_MSG = _('Request timeout error')


class InstantDisbursementAPIView(views.APIView):
    """
    Handles instant disbursement/cash_in POST requests
    """

    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope, IsInstantAPICheckerUser]
    throttle_classes = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.specific_issuers = ['orange', 'aman', 'bank_wallet', 'bank_card']

    def get_superadmin_pin(self, instant_user, wallet_issuer, serializer):
        """
        Placed at the .env, formatted like {InstantSuperUsername}_{issuer}_PIN=pin
        :param instant_user: the user who can initiate the instant cash in request
        :param wallet_issuer: type of the passed wallet issuer
        :param serializer: the serializer which contains the data
        :return: It returns the PIN of the instant user's superadmin from request's data or .env file
        """
        if wallet_issuer.lower() in self.specific_issuers: return True

        if serializer.data.get('is_single_step', None) or \
            not serializer.data.get('pin', None):
            return get_from_env(f"{instant_user.root.super_admin.username}_{wallet_issuer}_PIN")

        return serializer.validated_data['pin']

    def match_issuer_type(self, issuer):
        """
        Match the wallet issuer used at the request with its corresponding one at the issuer choices
        :param issuer: issuer passed from the serializer
        :return: choice letter that match the issuer type at the model
        """
        for choice in InstantTransaction.ISSUER_TYPE_CHOICES:
            if issuer.lower() == choice[1].lower():
                return choice[0]
        return 'V'

    def determine_trx_category_and_purpose(self, transaction_type):
        """Determine transaction category code and purpose based on the passed transaction_type"""
        if transaction_type.upper() == "MOBILE":
            category_purpose_dict = {
                "category_code": "MOBI",
                "purpose": "CASH"
            }
        elif transaction_type.upper() == "SALARY":
            category_purpose_dict = {
                "category_code": "CASH",
                "purpose": "SALA"
            }
        elif transaction_type.upper() == "PREPAID_CARD":
            category_purpose_dict = {
                "category_code": "PCRD",
                "purpose": "CASH"
            }
        elif transaction_type.upper() == "CREDIT_CARD":
            category_purpose_dict = {
                "category_code": "CASH",
                "purpose": "CCRD"
            }
        else:
            category_purpose_dict = {
                "category_code": "CASH",
                "purpose": "CASH"
            }

        return category_purpose_dict

    def create_bank_transaction(self, disburser, serializer):
        """Create a bank transaction out of the passed serializer data"""
        amount = serializer.validated_data["amount"]
        issuer = serializer.validated_data["issuer"].lower()
        full_name = serializer.validated_data["full_name"]
        client_reference_id = serializer.validated_data.get("client_reference_id")
        instant_transaction = False
        fees, vat = disburser.root.budget.calculate_fees_and_vat_for_amount(
            amount, issuer
        )
        if issuer in ["bank_wallet", "orange"]:
            creditor_account_number = serializer.validated_data["msisdn"]
            creditor_bank = "MIDG" if get_from_env("ENVIRONMENT") != "staging" else "THWL"     # ToDo: Should be "THWL" at the staging environment
            transaction_type = "MOBILE"
            instant_transaction = InstantTransaction.objects.create(
                    from_user=disburser, anon_recipient=creditor_account_number, amount=amount,
                    issuer_type=self.match_issuer_type(issuer), recipient_name=full_name,
                    is_single_step=serializer.validated_data["is_single_step"],
                    fees=fees, vat=vat,
                    client_transaction_reference = client_reference_id
                    #disbursed_date=timezone.now()
            )
        else:
            creditor_account_number = get_digits(serializer.validated_data["bank_card_number"])
            creditor_bank = serializer.validated_data["bank_code"]
            transaction_type = serializer.validated_data["bank_transaction_type"]

        transaction_dict = {
            "currency": "EGP",
            "debtor_address_1": "EG",
            "creditor_address_1": "EG",
            "corporate_code": get_from_env("ACH_CORPORATE_CODE"),
            "debtor_account": get_from_env("ACH_DEBTOR_ACCOUNT"),
            "user_created": disburser,
            "amount": amount,
            "creditor_name": full_name,
            "creditor_account_number": creditor_account_number,
            "creditor_bank": creditor_bank,
            "end_to_end": "" if issuer == "bank_card" else instant_transaction.uid,
            "disbursed_date": timezone.now() if issuer == "bank_card" else instant_transaction.disbursed_date,
            "is_single_step":serializer.validated_data["is_single_step"],
            "client_transaction_reference":client_reference_id,
            "fees": fees,
            "vat": vat
        }
        transaction_dict.update(self.determine_trx_category_and_purpose(transaction_type))
        bank_transaction = BankTransaction.objects.create(**transaction_dict)
        return bank_transaction, instant_transaction

    def aman_api_authentication_params(self, aman_channel_object):
        """Handle retrieving token/merchant_id from api_authentication method of aman channel"""
        api_auth_response = aman_channel_object.api_authentication()
        api_auth_token = merchant_id = None

        if api_auth_response.status_code == status.HTTP_201_CREATED:
            api_auth_token = api_auth_response.data.get('api_auth_token', '')
            merchant_id = str(api_auth_response.data.get('merchant_id', ''))

        return api_auth_token, merchant_id

    def aman_issuer_handler(self, request, transaction_object, serializer, user):
        """Handle aman operations/transactions separately"""

        aman_object = AmanChannel(request, transaction_object, user=user)

        try:
            api_auth_token, merchant_id = self.aman_api_authentication_params(aman_object)
            order_registration = aman_object.order_registration(api_auth_token, merchant_id, transaction_object.uid)

            if order_registration.status_code == status.HTTP_201_CREATED:
                api_auth_token, _ = self.aman_api_authentication_params(aman_object)
                payment_key_params = {
                    "api_auth_token": api_auth_token,
                    "order_id": order_registration.data.get('order_id', ''),
                    "first_name": f"{serializer.validated_data['first_name']}",
                    "last_name": f"{serializer.validated_data['last_name']}",
                    "email": f"{serializer.validated_data['email']}",
                    "phone_number": f"+2{serializer.validated_data['msisdn']}"
                }
                payment_key_obtained = aman_object.obtain_payment_key(**payment_key_params)

                if payment_key_obtained.status_code == status.HTTP_201_CREATED:
                    payment_key = payment_key_obtained.data.get('payment_token', '')
                    make_payment_request = aman_object.make_pay_request(payment_key)

                    if make_payment_request.status_code == status.HTTP_200_OK:
                        return make_payment_request

        except Exception as err:
            aman_object.log_message(request, f"[failed instant trx]", f"exception: {err.args[0]}")
            transaction_object.mark_failed(status.HTTP_424_FAILED_DEPENDENCY, EXTERNAL_ERROR_MSG)
            return Response(InstantTransactionResponseModelSerializer(transaction_object).data)

    def post(self, request, *args, **kwargs):
        """
        Handles POST HTTP requests
        """
        serializer = InstantDisbursementRequestSerializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            if 'user' in serializer.validated_data:
                user = User.objects.get(username=serializer.validated_data['user'])
            else:
                user = request.user

            if not user.root.\
                    budget.within_threshold(serializer.validated_data['amount'], serializer.validated_data['issuer']):
                raise ValidationError(BUDGET_EXCEEDED_MSG)
        except (ValidationError, ValueError, Exception) as e:
            if len(serializer.errors) > 0:
                failure_message = serializer.errors
            elif e.args[0] == BUDGET_EXCEEDED_MSG:
                failure_message = BUDGET_EXCEEDED_MSG
            else:
                failure_message = INTERNAL_ERROR_MSG
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[message] [VALIDATION ERROR]", request, e.args)
            return Response({
                "disbursement_status": _("failed"), "status_description": failure_message,
                "status_code": str(status.HTTP_400_BAD_REQUEST)
            }, status=status.HTTP_400_BAD_REQUEST)

        issuer = serializer.validated_data["issuer"].lower()

        if issuer in ["vodafone", "etisalat", "aman"]:
            transaction = None

            try:
                instant_user = user
                vmt_data = VMTData.objects.get(vmt=instant_user.root.client.creator)
                data_dict = vmt_data.return_vmt_data(VMTData.INSTANT_DISBURSEMENT)
                data_dict['MSISDN2'] = serializer.validated_data["msisdn"]
                data_dict['AMOUNT'] = str(serializer.validated_data["amount"])
                data_dict['WALLETISSUER'] = issuer.upper()

                if issuer not in self.specific_issuers:
                    data_dict['MSISDN'] = instant_user.root.super_admin.first_non_super_agent(issuer)

                if issuer.lower() == 'aman':
                    full_name = f"{serializer.validated_data['first_name']} {serializer.validated_data['last_name']}"
                else:
                    full_name = ""
                fees, vat = user.root.budget.calculate_fees_and_vat_for_amount(
                    data_dict['AMOUNT'], issuer
                )
                transaction = InstantTransaction.objects.create(
                        from_user=user, anon_recipient=data_dict['MSISDN2'], status="P",
                        amount=data_dict['AMOUNT'], issuer_type=self.match_issuer_type(data_dict['WALLETISSUER']),
                        anon_sender=data_dict['MSISDN'], recipient_name=full_name, is_single_step=serializer.validated_data["is_single_step"],
                        disbursed_date=timezone.now(), fees=fees, vat=vat,
                        client_transaction_reference=serializer.validated_data.get("client_reference_id")
                )
                
                data_dict['PIN'] = self.get_superadmin_pin(instant_user, data_dict['WALLETISSUER'], serializer)

            except Exception as e:
                if transaction:transaction.mark_failed(status.HTTP_500_INTERNAL_SERVER_ERROR, INTERNAL_ERROR_MSG)
                logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[message] [INTERNAL SYSTEM ERROR]", request, e.args)
                return default_response_structure(
                        transaction_id=transaction.uid if transaction else None,
                        status_description={"Internal Error": INTERNAL_ERROR_MSG},
                        field_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # if issuer etisalat add uid to the payload
            if issuer == 'etisalat':
                data_dict['EXTREFNUM'] = str(transaction.uid)
            
            request_data_dictionary_without_pins = copy.deepcopy(data_dict)
            request_data_dictionary_without_pins['PIN'] = 'xxxxxx'
            logging_message(
                INSTANT_CASHIN_REQUEST_LOGGER, "[request] [DATA DICT TO CENTRAL]", request,
                f"{request_data_dictionary_without_pins}"
            )

            try:
                if issuer == "aman":
                    return self.aman_issuer_handler(request, transaction, serializer, user)

                # check if msisdn is test number
                if get_from_env("ENVIRONMENT") in ['staging', 'local'] and \
                    issuer in ['vodafone', 'etisalat'] and \
                    data_dict['MSISDN2'] == get_from_env(f"test_number_for_{issuer}"):
                    transaction.mark_successful(200, "")
                    user.root.budget.update_disbursed_amount_and_current_balance(data_dict['AMOUNT'], issuer)
                    return Response(InstantTransactionResponseModelSerializer(transaction).data, status=status.HTTP_200_OK)

                trx_response = requests.post(
                    get_from_env(vmt_data.vmt_environment), json=data_dict, verify=False,
                    timeout=TIMEOUT_CONSTANTS["CENTRAL_UIG"]
                )

                if trx_response.ok:
                    json_trx_response = trx_response.json()
                    transaction.reference_id = json_trx_response["TXNID"]
                else:
                    raise ImproperlyConfigured(trx_response.text)

            except ValidationError as e:
                logging_message(
                        INSTANT_CASHIN_FAILURE_LOGGER, "[message] [DISBURSEMENT VALIDATION ERROR]", request, e.args
                )
                transaction.mark_failed(status.HTTP_500_INTERNAL_SERVER_ERROR, INTERNAL_ERROR_MSG)
                return Response(InstantTransactionResponseModelSerializer(transaction).data, status=status.HTTP_200_OK)

            except (requests.Timeout, TimeoutError) as e:
                logging_message(
                    INSTANT_CASHIN_FAILURE_LOGGER, "[response] [ERROR FROM CENTRAL]", request, f"timeout, {e.args}"
                )
                transaction.mark_unknown(status.HTTP_408_REQUEST_TIMEOUT, TIMEOUT_ERROR_MSG)
                return Response(InstantTransactionResponseModelSerializer(transaction).data, status=status.HTTP_200_OK)

            except (ImproperlyConfigured, Exception) as e:
                logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[response] [ERROR FROM CENTRAL]", request, e.args)
                transaction.mark_failed(status.HTTP_424_FAILED_DEPENDENCY, EXTERNAL_ERROR_MSG)
                return Response(InstantTransactionResponseModelSerializer(transaction).data, status=status.HTTP_200_OK)

            if json_trx_response["TXNSTATUS"] == "200":
                logging_message(
                        INSTANT_CASHIN_SUCCESS_LOGGER, "[response] [SUCCESSFUL TRX]", request, f"{json_trx_response}"
                )
                transaction.mark_successful(json_trx_response["TXNSTATUS"], json_trx_response["MESSAGE"])
                user.root.budget.update_disbursed_amount_and_current_balance(data_dict['AMOUNT'], issuer)
                return Response(InstantTransactionResponseModelSerializer(transaction).data, status=status.HTTP_200_OK)
            elif json_trx_response["TXNSTATUS"] == "501" or \
                 json_trx_response["TXNSTATUS"] == "-1" or \
                 json_trx_response["TXNSTATUS"] == "6005" :
                logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[response] [FAILED TRX]", request, f"timeout, {json_trx_response}")
                transaction.mark_unknown(json_trx_response["TXNSTATUS"], json_trx_response["MESSAGE"])
                return Response(InstantTransactionResponseModelSerializer(transaction).data, status=status.HTTP_200_OK)


            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[response] [FAILED TRX]", request, f"{json_trx_response}")
            transaction.mark_failed(json_trx_response["TXNSTATUS"], json_trx_response["MESSAGE"])
            return Response(InstantTransactionResponseModelSerializer(transaction).data, status=status.HTTP_200_OK)

        elif issuer in ["bank_wallet", "bank_card", "orange"]:

            try:
                bank_trx_obj, instant_trx_obj = self.create_bank_transaction(user, serializer)
            except Exception as e:
                logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[message] [ACH EXCEPTION]", request, e.args)
                return default_response_structure(
                        transaction_id=None, status_description={"Internal Error": INTERNAL_ERROR_MSG},
                        field_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, response_status_code=status.HTTP_200_OK
                )

            # check if msisdn is test number
            if get_from_env("ENVIRONMENT") in ['staging', 'local'] and \
                    issuer in ['orange', 'bank_wallet'] and \
                    instant_trx_obj.anon_recipient == get_from_env(f"test_number_for_{issuer}"):

                bank_trx_obj.mark_successful("8333", "success")
                instant_trx_obj.mark_successful("8222", "success") if instant_trx_obj else None
                bank_trx_obj.user_created.root. \
                    budget.update_disbursed_amount_and_current_balance(bank_trx_obj.amount, issuer)
                return Response(InstantTransactionResponseModelSerializer(instant_trx_obj).data)

            return BankTransactionsChannel.send_transaction(bank_trx_obj, instant_trx_obj)


class SingleStepDisbursementAPIView(InstantDisbursementAPIView):
   
    permission_classes = []
