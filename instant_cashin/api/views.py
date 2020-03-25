import logging

import requests

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope, permissions
from rest_framework import status, views
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from data.utils import get_client_ip
from disb.models import VMTData

from ..utils import default_response_structure, get_from_env, logging_message
from .serializers import InstantUserInquirySerializer, InstantDisbursementSerializer
from ..models.instant_transactions import InstantTransaction
from .mixins import IsInstantAPICheckerUser


INSTANT_CASHIN_SUCCESS_LOGGER = logging.getLogger("instant_cashin_success")
INSTANT_CASHIN_FAILURE_LOGGER = logging.getLogger("instant_cashin_failure")
INSTANT_CASHIN_REQUEST_LOGGER = logging.getLogger("instant_cashin_requests")

INTERNAL_ERROR_MSG = _("Process stopped during an internal error, can you try again or contact your support team.")
EXTERNAL_ERROR_MSG = _("Process stopped during an external error, can you try again or contact your support team.")


class InstantUserInquiryAPIView(views.APIView):
    """
    Handles instant user/wallet inquiry POST requests
    """

    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope]

    def custom_response(self,
                        head="wallet_status",
                        head_message="valid vodafone-cash wallet.",
                        next_trial="300",
                        status_code=status.HTTP_200_OK):
        """
        :return: returns general response
        """
        return Response({
            f"{head}": _(f"{head_message}"),
            "next_trial": int(next_trial)
        }, status=status_code)

    def post(self, request, *args, **kwargs):
        """
        Handles POST HTTP requests to this inquire-user API endpoint
        """
        serializer = InstantUserInquirySerializer(data=request.data)
        json_inquiry_response = "Request time out"      # If it's empty then log it as request timed out

        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[VALIDATION ERROR - USER INQUIRY]", serializer.errors)
            return Response({"Validation Error": e.args[0]}, status.HTTP_400_BAD_REQUEST)

        try:
            instant_user = get_object_or_404(get_user_model(), username=request.user.username)
            vmt_data = VMTData.objects.get(vmt=instant_user.root.client.creator)
            data_dict = vmt_data.return_vmt_data(VMTData.USER_INQUIRY)
            data_dict['USERS'] = [serializer.validated_data["msisdn"]]       # It must be a list
        except Exception as e:
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[INTERNAL ERROR - USER INQUIRY]", e.args[0])
            return self.custom_response(
               head="Internal Error", head_message=INTERNAL_ERROR_MSG, status_code=status.HTTP_424_FAILED_DEPENDENCY
            )

        try:
            logging_message(
                    INSTANT_CASHIN_REQUEST_LOGGER, "[Request Data - USER INQUIRY]",
                    f"Ip Address: {get_client_ip(request)}, vmt_env used: {vmt_data.vmt_environment}\n\t"
                    f"Data dictionary: {data_dict}"
            )
            inquiry_response = requests.post(get_from_env(vmt_data.vmt_environment), json=data_dict, verify=False)
            json_inquiry_response = inquiry_response.json()
        except (TimeoutError, ImproperlyConfigured, Exception) as e:
            log_msg = e.args[0]
            if json_inquiry_response != "Request time out":
                log_msg = json_inquiry_response.content
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[UIG ERROR - USER INQUIRY]", log_msg)
            return self.custom_response(head="External Error", head_message=EXTERNAL_ERROR_MSG)

        log_msg = f"USER: {request.user.username} inquired for user with MSISDN {serializer.validated_data['msisdn']}" \
                  f"\n\tResponse content: {json_inquiry_response}"

        if inquiry_response.ok and json_inquiry_response["TRANSACTIONS"][0]["WALLET_STATUS"] == "Active":
            logging_message(INSTANT_CASHIN_SUCCESS_LOGGER, "[INSTANT USER INQUIRY]", log_msg)
            return self.custom_response()

        logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[FAILED INSTANT USER INQUIRY]", log_msg)
        return self.custom_response(head_message="not valid vodafone-cash wallet.")


class InstantDisbursementAPIView(views.APIView):
    """
    Handles instant disbursement/cash_in POST requests
    """

    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope, IsInstantAPICheckerUser]

    def root_corresponding_pin(self, instant_user, serializer):
        """
        :param instant_user: the user who can initiate the instant cash in request
        :param serializer: the serializer which contains the data
        :return: It returns the PIN of the instant user's root from request's data or .env file
        """
        if not serializer.data['pin']:
            return get_from_env(f"{instant_user.root.username}_PIN")
        return serializer.validated_data['pin']

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
            instant_user = get_object_or_404(get_user_model(), username=request.user.username)
            vmt_data = VMTData.objects.get(vmt=instant_user.root.client.creator)
            data_dict = vmt_data.return_vmt_data(VMTData.INSTANT_DISBURSEMENT)
            data_dict['MSISDN'] = instant_user.root.first_non_super_agent()
            data_dict['MSISDN2'] = serializer.validated_data["msisdn"]
            data_dict['AMOUNT'] = str(serializer.validated_data["amount"])
            data_dict['PIN'] = self.root_corresponding_pin(instant_user, serializer)
        except Exception as e:
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[INTERNAL ERROR - INSTANT CASHIN]", e.args[0])
            return default_response_structure(
                    status_description={"Internal Error": INTERNAL_ERROR_MSG},
                    field_status_code=status.HTTP_424_FAILED_DEPENDENCY
            )

        try:
            logging_message(
                    INSTANT_CASHIN_REQUEST_LOGGER, "[Request Data - INSTANT CASHIN]",
                    f"Ip Address: {get_client_ip(request)}, vmt_env used: {vmt_data.vmt_environment}\n\t"
                    f"Data dictionary: {data_dict}"
            )
            transaction = InstantTransaction.objects.create(
                    from_user=request.user, anon_sender=data_dict['MSISDN'], anon_recipient=data_dict['MSISDN2'],
                    status="F", amount=data_dict['AMOUNT']
            )
            if not request.user.budget.within_threshold(serializer.validated_data['amount']):
                msg = _("Sorry, the amount to be disbursed exceeds you budget limit.")
                raise ValidationError(msg)
            inquiry_response = requests.post(get_from_env(vmt_data.vmt_environment), json=data_dict, verify=False)
            json_inquiry_response = inquiry_response.json()
        except ValidationError as e:
            if transaction:
                transaction.failure_reason = e.args[0]
                transaction.save()
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
                transaction.save()
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[UIG ERROR - INSTANT CASHIN]", log_msg)

            return default_response_structure(
                    status_description=EXTERNAL_ERROR_MSG, field_status_code=status.HTTP_424_FAILED_DEPENDENCY,
                    response_status_code=status.HTTP_200_OK
            )

        log_msg = f"USER: {request.user.username} disbursed: {data_dict['AMOUNT']}EG for " \
                  f"MSISDN: {data_dict['MSISDN2']}\n\tResponse content: {json_inquiry_response}"

        if inquiry_response.ok and json_inquiry_response["TXNSTATUS"] == "200":
            logging_message(INSTANT_CASHIN_SUCCESS_LOGGER, "[INSTANT CASHIN]", log_msg)
            transaction.mark_successful()
            request.user.budget.update_disbursed_amount(data_dict['AMOUNT'])
            return default_response_structure(
                    status_description=json_inquiry_response["MESSAGE"],
                    disbursement_status=_("success"), response_status_code=status.HTTP_200_OK
            )

        logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[FAILED INSTANT CASHIN]", log_msg)
        if transaction:
            transaction.failure_reason = json_inquiry_response["MESSAGE"]   # Save the full failure reason
            transaction.save()
        return default_response_structure(
                status_description=json_inquiry_response["MESSAGE"],
                field_status_code=json_inquiry_response["TXNSTATUS"], response_status_code=status.HTTP_200_OK
        )
