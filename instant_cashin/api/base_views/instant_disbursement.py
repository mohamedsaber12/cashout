# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import logging

import requests

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext as _

from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope, permissions
from rest_framework import status, views
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from disbursement.models import VMTData
from utilities.logging import logging_message

from ..serializers import InstantDisbursementSerializer
from ...specific_issuers_integrations import AmanChannel
from ..mixins import IsInstantAPICheckerUser
from ...models import InstantTransaction
from ...utils import default_response_structure, get_from_env


INSTANT_CASHIN_SUCCESS_LOGGER = logging.getLogger("instant_cashin_success")
INSTANT_CASHIN_FAILURE_LOGGER = logging.getLogger("instant_cashin_failure")
INSTANT_CASHIN_PENDING_LOGGER = logging.getLogger("instant_cashin_pending")
INSTANT_CASHIN_REQUEST_LOGGER = logging.getLogger("instant_cashin_requests")

INTERNAL_ERROR_MSG = _("Process stopped during an internal error, can you try again or contact your support team.")
EXTERNAL_ERROR_MSG = _("Process stopped during an external error, can you try again or contact your support team.")
ORANGE_PENDING_MSG = _("Your transaction will be process the soonest, wait for a response at the next 24 hours.")
BUDGET_EXCEEDED_MSG = _("Sorry, the amount to be disbursed exceeds you budget limit. please contact your support team.")


class InstantDisbursementAPIView(views.APIView):
    """
    Handles instant disbursement/cash_in POST requests
    """

    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope, IsInstantAPICheckerUser]
    throttle_classes = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.specific_issuers = ['orange', 'aman']

    def superadmin_corresponding_pin(self, instant_user, wallet_issuer, serializer):
        """
        Placed at the .env, formatted like {InstantSuperUsername}_{issuer}_PIN=pin
        :param instant_user: the user who can initiate the instant cash in request
        :param wallet_issuer: type of the passed wallet issuer
        :param serializer: the serializer which contains the data
        :return: It returns the PIN of the instant user's superadmin from request's data or .env file
        """
        if wallet_issuer.lower() in self.specific_issuers: return True

        if not serializer.data['pin']:
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

    def aman_api_authentication_params(self, aman_channel_object):
        """Handle retrieving token/merchant_id from api_authentication method of aman channel"""
        api_auth_response = aman_channel_object.api_authentication()

        if api_auth_response.status_code == status.HTTP_201_CREATED:
            api_auth_token = api_auth_response.data.get('api_auth_token', '')
            merchant_id = str(api_auth_response.data.get('merchant_id', ''))

            return api_auth_token, merchant_id

    def aman_issuer_handler(self, request, transaction_object, serializer):
        """Handle aman operations/transactions separately"""

        aman_object = AmanChannel(request, transaction_object)

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
            aman_object.log_message(request, f"[GENERAL FAILURE - AMAN CHANNEL]", f"Exception: {err.args[0]}")

        raise Exception(EXTERNAL_ERROR_MSG)

    def orange_issuer_handler(self, request, transaction_object, serializer):
        """Handle orange operations/transactions separately"""

        logging_message(
                INSTANT_CASHIN_PENDING_LOGGER, "[PENDING TRX]", request, f"Data dict: {serializer.validated_data}"
        )

        return default_response_structure(
                transaction_object.uid, disbursement_status=_("pending"), status_description=ORANGE_PENDING_MSG,
                field_status_code=status.HTTP_202_ACCEPTED, response_status_code=status.HTTP_200_OK
        )

    def post(self, request, *args, **kwargs):
        """
        Handles POST HTTP requests
        """
        serializer = InstantDisbursementSerializer(data=request.data)
        json_inquiry_response = "Request time out"      # If it's empty then log it as request timed out
        transaction = None

        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[SERIALIZER VALIDATION ERROR]", request, serializer.errors)
            return Response({
                "disbursement_status": _("failed"), "status_description": e.args[0],
                "status_code": str(status.HTTP_400_BAD_REQUEST)
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            instant_user = request.user
            vmt_data = VMTData.objects.get(vmt=instant_user.root.client.creator)
            data_dict = vmt_data.return_vmt_data(VMTData.INSTANT_DISBURSEMENT)
            data_dict['MSISDN2'] = serializer.validated_data["msisdn"]
            data_dict['AMOUNT'] = str(serializer.validated_data["amount"])
            issuer = data_dict['WALLETISSUER'] = serializer.validated_data["issuer"]

            if issuer.lower() not in self.specific_issuers:
                data_dict['MSISDN'] = instant_user.root.first_non_super_agent(serializer.validated_data["issuer"])

            transaction = InstantTransaction.objects.create(
                    from_user=request.user, anon_recipient=data_dict['MSISDN2'], status="P", amount=data_dict['AMOUNT'],
                    issuer_type=self.match_issuer_type(data_dict['WALLETISSUER']), anon_sender=data_dict['MSISDN']
            )
            data_dict['PIN'] = self.superadmin_corresponding_pin(instant_user, data_dict['WALLETISSUER'], serializer)

        except Exception as e:
            if transaction: transaction.mark_failed(INTERNAL_ERROR_MSG)
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[INTERNAL SYSTEM ERROR]", request, e.args)
            return default_response_structure(
                    transaction_id=transaction.uid, status_description={"Internal Error": INTERNAL_ERROR_MSG},
                    field_status_code=status.HTTP_424_FAILED_DEPENDENCY
            )

        request_data_dictionary_without_pins = copy.deepcopy(data_dict)
        request_data_dictionary_without_pins['PIN'] = 'xxxxxx'
        logging_message(
                INSTANT_CASHIN_REQUEST_LOGGER, "[REQUEST DATA DICT TO CENTRAL]", request,
                f"Data dictionary: {request_data_dictionary_without_pins}"
        )

        try:
            if not request.user.root.budget.within_threshold(serializer.validated_data['amount'], issuer.lower()):
                raise ValidationError(BUDGET_EXCEEDED_MSG)

            if issuer.lower() in self.specific_issuers:
                specific_issuer_handler = getattr(self, f"{issuer.lower()}_issuer_handler")
                specific_issuer_response = specific_issuer_handler(request, transaction, serializer)

                if isinstance(specific_issuer_response, Response):
                    return specific_issuer_response

            inquiry_response = requests.post(get_from_env(vmt_data.vmt_environment), json=data_dict, verify=False)
            json_inquiry_response = inquiry_response.json()

        except ValidationError as e:
            trx_failure_msg = INTERNAL_ERROR_MSG if e.args[0] != BUDGET_EXCEEDED_MSG else BUDGET_EXCEEDED_MSG
            if transaction: transaction.mark_failed(trx_failure_msg)
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[DISBURSEMENT VALIDATION ERROR]", request, e.args)
            return default_response_structure(
                    transaction_id=transaction.uid, status_description=e.args[0],
                    field_status_code="6061", response_status_code=status.HTTP_200_OK
            )

        except (TimeoutError, ImproperlyConfigured, Exception) as e:
            log_msg = e.args[0]
            if json_inquiry_response != "Request time out": log_msg = json_inquiry_response.content
            if transaction: transaction.mark_failed(EXTERNAL_ERROR_MSG)
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[ERROR FROM CENTRAL]", request, log_msg)
            return default_response_structure(
                    transaction_id=transaction.uid, status_description=EXTERNAL_ERROR_MSG,
                    field_status_code=status.HTTP_424_FAILED_DEPENDENCY, response_status_code=status.HTTP_200_OK
            )

        if inquiry_response.ok and json_inquiry_response["TXNSTATUS"] == "200":
            logging_message(INSTANT_CASHIN_SUCCESS_LOGGER, "[SUCCESSFUL TRX]", request, f"{json_inquiry_response}")
            transaction.mark_successful()
            request.user.root.budget.update_disbursed_amount_and_current_balance(data_dict['AMOUNT'], issuer.lower())
            return default_response_structure(
                    transaction_id=transaction.uid, status_description=json_inquiry_response["MESSAGE"],
                    disbursement_status=_("success"), response_status_code=status.HTTP_200_OK
            )

        logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[FAILED TRX]", request, f"{json_inquiry_response}")
        if transaction: transaction.mark_failed(json_inquiry_response["MESSAGE"])
        return default_response_structure(
                transaction_id=transaction.uid, status_description=json_inquiry_response["MESSAGE"],
                field_status_code=json_inquiry_response["TXNSTATUS"], response_status_code=status.HTTP_200_OK
        )
