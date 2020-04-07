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

from data.utils import get_client_ip
from disb.models import VMTData

from ...utils import default_response_structure, get_from_env, logging_message
from ..serializers import InstantDisbursementSerializer
from ...models.instant_transactions import InstantTransaction
from ..mixins import IsInstantAPICheckerUser


INSTANT_CASHIN_SUCCESS_LOGGER = logging.getLogger("instant_cashin_success")
INSTANT_CASHIN_FAILURE_LOGGER = logging.getLogger("instant_cashin_failure")
INSTANT_CASHIN_PENDING_LOGGER = logging.getLogger("instant_cashin_pending")
INSTANT_CASHIN_REQUEST_LOGGER = logging.getLogger("instant_cashin_requests")

INTERNAL_ERROR_MSG = _("Process stopped during an internal error, can you try again or contact your support team.")
EXTERNAL_ERROR_MSG = _("Process stopped during an external error, can you try again or contact your support team.")
ORANGE_PENDING_MSG = _("Your transaction will be process the soonest, wait for a response at the next 24 hours.")


class InstantDisbursementAPIView(views.APIView):
    """
    Handles instant disbursement/cash_in POST requests
    """

    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope, IsInstantAPICheckerUser]
    throttle_classes = []

    def root_corresponding_pin(self, instant_user, wallet_issuer, serializer):
        """
        Placed at the .env, formatted like {InstantRootUsername}_{issuer}_PIN=pin
        :param instant_user: the user who can initiate the instant cash in request
        :param wallet_issuer: type of the passed wallet issuer
        :param serializer: the serializer which contains the data
        :return: It returns the PIN of the instant user's root from request's data or .env file
        """
        if wallet_issuer == "ORANGE": return True
        if not serializer.data['pin']:
            return get_from_env(f"{instant_user.root.username}_{wallet_issuer}_PIN")
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
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[VALIDATION ERROR - INSTANT CASHIN]", serializer.errors)
            return default_response_structure(
                    status_description=e.args[0], field_status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            instant_user = request.user
            vmt_data = VMTData.objects.get(vmt=instant_user.root.client.creator)
            data_dict = vmt_data.return_vmt_data(VMTData.INSTANT_DISBURSEMENT)
            data_dict['MSISDN'] = instant_user.root.first_non_super_agent(serializer.validated_data["issuer"])
            data_dict['MSISDN2'] = serializer.validated_data["msisdn"]
            data_dict['AMOUNT'] = str(serializer.validated_data["amount"])
            data_dict['WALLETISSUER'] = serializer.validated_data["issuer"]
            data_dict['PIN'] = self.root_corresponding_pin(instant_user, data_dict['WALLETISSUER'], serializer)
        except Exception as e:
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[INTERNAL ERROR - INSTANT CASHIN]", e.args[0])
            return default_response_structure(
                    status_description={"Internal Error": INTERNAL_ERROR_MSG},
                    field_status_code=status.HTTP_424_FAILED_DEPENDENCY
            )

        try:
            request_data_dictionary_without_pins = copy.deepcopy(data_dict)
            request_data_dictionary_without_pins['PIN'] = 'xxxxxx'
            logging_message(
                    INSTANT_CASHIN_REQUEST_LOGGER, "[Request Data - INSTANT CASHIN]",
                    f"Ip Address: {get_client_ip(request)}, vmt_env used: {vmt_data.vmt_environment}\n\t"
                    f"Data dictionary: {request_data_dictionary_without_pins}"
            )
            transaction = InstantTransaction.objects.create(
                    from_user=request.user, anon_recipient=data_dict['MSISDN2'], status="P", amount=data_dict['AMOUNT'],
                    issuer_type=self.match_issuer_type(data_dict['WALLETISSUER']), anon_sender=data_dict['MSISDN']
            )
            if not request.user.budget.within_threshold(serializer.validated_data['amount']):
                msg = _("Sorry, the amount to be disbursed exceeds you budget limit.")
                raise ValidationError(msg)

            if data_dict['WALLETISSUER'] == "ORANGE":
                transaction.blank_anon_sender()
                logging_message(
                        INSTANT_CASHIN_PENDING_LOGGER, "[PENDING - INSTANT CASHIN]",
                        f"User: {instant_user.username}, has pending trx with amount: {data_dict['AMOUNT']}EG "
                        f"for MSISDN: {data_dict['MSISDN2']}"
                )
                return default_response_structure(
                        disbursement_status=_("pending"), status_description=ORANGE_PENDING_MSG,
                        field_status_code=status.HTTP_202_ACCEPTED, response_status_code=status.HTTP_200_OK
                )

            inquiry_response = requests.post(get_from_env(vmt_data.vmt_environment), json=data_dict, verify=False)
            json_inquiry_response = inquiry_response.json()

        except ValidationError as e:
            if transaction:
                transaction.failure_reason = INTERNAL_ERROR_MSG
                transaction.mark_failed()
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[Validation Error - INSTANT CASHIN]", e.args[0])
            return default_response_structure(
                    status_description=e.args[0], field_status_code="6061", response_status_code=status.HTTP_200_OK
            )

        except (TimeoutError, ImproperlyConfigured, Exception) as e:
            log_msg = e.args[0]
            if json_inquiry_response != "Request time out":
                log_msg = json_inquiry_response.content
            if transaction:
                transaction.failure_reason = log_msg
                transaction.mark_failed()
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[UIG ERROR - INSTANT CASHIN]", log_msg)
            return default_response_structure(
                    status_description=EXTERNAL_ERROR_MSG, field_status_code=status.HTTP_424_FAILED_DEPENDENCY,
                    response_status_code=status.HTTP_200_OK
            )

        log_msg = f"USER: {request.user.username} disbursed: {data_dict['AMOUNT']}EG for " \
                  f"MSISDN: {data_dict['MSISDN2']}\n\tResponse content: {json_inquiry_response}"

        if inquiry_response.ok and json_inquiry_response["TXNSTATUS"] == "200":
            logging_message(INSTANT_CASHIN_SUCCESS_LOGGER, "[SUCCESSFUL - INSTANT CASHIN]", log_msg)
            transaction.mark_successful()
            request.user.budget.update_disbursed_amount(data_dict['AMOUNT'])
            return default_response_structure(
                    status_description=json_inquiry_response["MESSAGE"],
                    disbursement_status=_("success"), response_status_code=status.HTTP_200_OK
            )

        logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[FAILED - INSTANT CASHIN]", log_msg)
        if transaction:
            transaction.failure_reason = json_inquiry_response["MESSAGE"]   # Save the full failure reason
            transaction.mark_failed()
        return default_response_structure(
                status_description=json_inquiry_response["MESSAGE"],
                field_status_code=json_inquiry_response["TXNSTATUS"], response_status_code=status.HTTP_200_OK
        )
