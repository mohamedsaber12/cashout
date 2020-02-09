import logging

import requests

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope, permissions
from rest_framework import status, views
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from disb.models import VMTData

from ..utils import get_corresponding_env_url, logging_message
from .serializers import InstantUserInquirySerializer


INSTANT_CASHIN_SUCCESS_LOGGER = logging.getLogger("instant_cashin_success")
INSTANT_CASHIN_FAILURE_LOGGER = logging.getLogger("instant_cashin_failure")


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

        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[VALIDATION ERROR]", serializer.errors)
            return Response({"Validation Error": e.args}, status.HTTP_400_BAD_REQUEST)

        try:
            instant_user = get_object_or_404(get_user_model(), username=request.user.username)
            vmt_credentials = VMTData.objects.get(vmt=instant_user.root.client.creator)
            data_dict = vmt_credentials.return_vmt_data(VMTData.USER_INQUIRY)
            data_dict['USERS'] = [serializer.validated_data["msisdn"]]       # It must be a list
        except Exception as e:
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[INTERNAL ERROR]", e.args)
            return self.custom_response(
               head="Internal Error",
               head_message="Process stopped during an internal error, can you try again or contact your support team.",
               status_code=status.HTTP_424_FAILED_DEPENDENCY
            )

        try:
            inquiry_response = requests.post(get_corresponding_env_url(vmt_credentials), json=data_dict, verify=False)
            json_inquiry_response = inquiry_response.json()
        except Exception:
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[UIG ERROR]", inquiry_response.content)
            return self.custom_response(
               head="External Error",
               head_message="Process stopped during an external error, can you try again or contact your support team.",
            )

        log_msg = f"USER: {request.user.username} inquired for user with MSISDN {serializer.validated_data['msisdn']}"

        if inquiry_response.ok and json_inquiry_response["TRANSACTIONS"][0]["WALLET_STATUS"] == "Active":
            logging_message(INSTANT_CASHIN_SUCCESS_LOGGER, "[INSTANT USER INQUIRY]", log_msg)
            return self.custom_response()

        logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[FAILED INSTANT USER INQUIRY]", log_msg)
        return self.custom_response(head_message="not valid vodafone-cash wallet.")
