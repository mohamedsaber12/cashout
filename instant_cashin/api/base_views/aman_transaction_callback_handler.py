# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import hashlib
import hmac
import logging

from django.utils.translation import gettext as _

from rest_framework import status, views
from rest_framework.response import Response

from utilities.logging import logging_message

from ...specific_issuers_integrations import AmanChannel
from ...utils import get_from_env


EXTERNAL_ERROR_MSG = _("Process stopped during an external error, can you try again or contact your support team.")
AMAN_LOGGER = logging.getLogger('aman_channel')


class AmanTransactionCallbackHandlerAPIView(views.APIView):
    """
    Handles aman transaction callback api view
    """

    @staticmethod
    def calculate_hmac(callback):
        amount_cents = str(callback.get("obj", "").get("amount_cents", ""))
        created_at = str(callback.get("obj", "").get("created_at", ""))
        currency = str(callback.get("obj", "").get("currency", ""))
        error_occured = str(callback.get("obj", "").get("error_occured", "")).lower()
        has_parent_transaction = str(callback.get("obj", "").get("has_parent_transaction", "")).lower()
        id = str(callback.get("obj", "").get("id", ""))
        integration_id = str(callback.get("obj", "").get("integration_id", ""))
        is_3d_secure = str(callback.get("obj", "").get("is_3d_secure", "")).lower()
        is_auth = str(callback.get("obj", "").get("is_auth", "")).lower()
        is_capture = str(callback.get("obj", "").get("is_capture", "")).lower()
        is_refunded = str(callback.get("obj", "").get("is_refunded", "")).lower()
        is_standalone_payment = str(callback.get("obj", "").get("is_standalone_payment", "")).lower()
        is_voided = str(callback.get("obj", "").get("is_voided", "")).lower()
        order_id = str(callback.get("obj", "").get("order", "").get("id", ""))
        owner = str(callback.get("obj", "").get("owner", ""))
        pending = str(callback.get("obj", "").get("pending", "")).lower()
        source_data_pan = str(callback.get("obj", "").get("source_data", "").get("pan", "")).lower()
        source_data_sub_type = str(callback.get("obj", "").get("source_data", "").get("sub_type", ""))
        source_data_type = str(callback.get("obj", "").get("source_data", "").get("type", "")).lower()
        success = str(callback.get("obj", "").get("success", "")).lower()

        calculated_hmac_string = amount_cents + created_at + currency + error_occured + has_parent_transaction + id + \
                                 integration_id + is_3d_secure + is_auth + is_capture + is_refunded + \
                                 is_standalone_payment + is_voided + order_id + owner + pending + source_data_pan + \
                                 source_data_sub_type + source_data_type + success
        calculated_hmac_string = calculated_hmac_string.encode("utf-8")
        hmac_secret = get_from_env(f"ACCEPT_HMAC_SECRET").encode("utf-8")
        calculated_hmac = hmac.new(hmac_secret, calculated_hmac_string, hashlib.sha512).hexdigest().lower()

        return calculated_hmac


    def post(self, request, *args, **kwargs):
        """Handles POST requests from Accept to update payment status of Aman transaction"""
        # ToDo: Add rate limit after 1000 at min

        try:
            calculated_hmac = self.calculate_hmac(request.data)
            received_hmac = request.GET.get("hmac")

            if calculated_hmac != received_hmac:
                raise ValueError(_("Hmac value mismatch!"))
        except ValueError as err:
            logging_message(AMAN_LOGGER, "[TRX CALLBACK HANDLER - HMAC ERROR]", request, f"Msg: {err.args}")
            return Response({"External Error": EXTERNAL_ERROR_MSG}, status=status.HTTP_400_BAD_REQUEST)

        updated_successfully, failure_reason = AmanChannel.notify_merchant(request.data)

        if updated_successfully:
            logging_message(
                    AMAN_LOGGER, "[TRX CALLBACK HANDLER - RECEIVED SUCCESSFULLY]", request, f"Response: {request.data}"
            )
            return Response({
                "Status": "Transaction status callback received successfully"
            }, status=status.HTTP_200_OK)
        else:
            logging_message(
                    AMAN_LOGGER, "[TRX CALLBACK HANDLER - ERROR]", request, f"Response: {request.data}"
            )
            return Response({"Status": "Transaction with this id is not found"}, status=status.HTTP_404_NOT_FOUND)
