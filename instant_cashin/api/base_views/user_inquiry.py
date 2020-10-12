# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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

from disbursement.models import VMTData
from utilities.logging import logging_message

from ...utils import get_from_env
from ..serializers import InstantUserInquirySerializer


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
            logging_message(
                    INSTANT_CASHIN_FAILURE_LOGGER, "[message] [VALIDATION ERROR - USER INQUIRY]",
                    request, serializer.errors
            )
            return Response({"Validation Error": e.args[0]}, status.HTTP_400_BAD_REQUEST)

        try:
            instant_user = get_object_or_404(get_user_model(), username=request.user.username)
            vmt_data = VMTData.objects.get(vmt=instant_user.root.client.creator)
            data_dict = vmt_data.return_vmt_data(VMTData.USER_INQUIRY)
            data_dict['USERS'] = [serializer.validated_data["msisdn"]]       # It must be a list
        except Exception as e:
            logging_message(
                    INSTANT_CASHIN_FAILURE_LOGGER, "[message] [INTERNAL ERROR - USER INQUIRY]", request, e.args[0]
            )
            return self.custom_response(
                    head="Internal Error", head_message=INTERNAL_ERROR_MSG, status_code=status.HTTP_424_FAILED_DEPENDENCY
            )

        try:
            logging_message(INSTANT_CASHIN_REQUEST_LOGGER, "[request] [USER INQUIRY]", request, f"{data_dict}")
            inquiry_response = requests.post(get_from_env(vmt_data.vmt_environment), json=data_dict, verify=False)
            json_inquiry_response = inquiry_response.json()
        except (TimeoutError, ImproperlyConfigured, Exception) as e:
            log_msg = e.args[0]
            if json_inquiry_response != "Request time out":
                log_msg = json_inquiry_response.content
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[message] [UIG ERROR - USER INQUIRY]", request, log_msg)
            return self.custom_response(head="External Error", head_message=EXTERNAL_ERROR_MSG)

        logging_message(
                INSTANT_CASHIN_FAILURE_LOGGER, "[response] [INSTANT USER INQUIRY]", request, json_inquiry_response
        )

        if inquiry_response.ok and json_inquiry_response["TRANSACTIONS"][0]["WALLET_STATUS"] == "Active":
            return self.custom_response()

        return self.custom_response(head_message="not valid vodafone-cash wallet.")
