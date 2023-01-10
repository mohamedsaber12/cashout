# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from decimal import Decimal

from django.utils.translation import gettext as _
from oauth2_provider.contrib.rest_framework import (TokenHasReadWriteScope,
                                                    permissions)
from rest_framework import status, views
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from users.models import User
from utilities.models import BalanceManagementOperations

from ..mixins import IsSystemAdminUser
from ..serializers import HoldBalanceRequestSerializer

BALANCE_MANAGEMENT_LOGGER = logging.getLogger("balance_management_operations")

INTERNAL_ERROR_MSG = _(
    "Process stopped during an internal error, can you try again or contact your support team"
)
NOT_ENOUGH_BALANCE_MSG = _("Sorry, you don't have enough balance")


class HoldBalanceAPIView(views.APIView):
    """
    hold balance for client
    """

    permission_classes = [
        permissions.IsAuthenticated,
        TokenHasReadWriteScope,
        IsSystemAdminUser,
    ]
    throttle_classes = []

    def post(self, request, *args, **kwargs):
        """
        Handles POST HTTP requests
        """
        serializer = HoldBalanceRequestSerializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            user = User.objects.filter(
                idms_user_id=serializer.validated_data['sso_user_id']
            ).first()
            (
                hold_balance_before,
                has_enough_balance,
            ) = user.root.budget.within_threshold_and_hold_balance_without_issuer(
                serializer.validated_data['amount']
            )

            # check for balance greater than amount then hold balance
            if not has_enough_balance:
                raise ValidationError(NOT_ENOUGH_BALANCE_MSG)

            # add new record in BalanceManagementOperations table
            BalanceManagementOperations.objects.create(
                operation_id=serializer.validated_data['operation_id'],
                source_product=serializer.validated_data['source_product'],
                operation_type="Hold",
                amount=serializer.validated_data['amount'],
                idms_user_id=serializer.validated_data['sso_user_id'],
                budget=user.root.budget,
                hold_balance_before=hold_balance_before,
                hold_balance_after=Decimal(hold_balance_before)
                + Decimal(serializer.validated_data['amount']),
            )
            BALANCE_MANAGEMENT_LOGGER.debug(
                f"[request] [API HOLD BALANCE] operation_id: {serializer.validated_data['operation_id']},"
                f" hold amount: {serializer.validated_data['amount']},"
                f" with idms_user_id: {serializer.validated_data['sso_user_id']},"
                f" from {serializer.validated_data['source_product']} product"
            )
            return Response(
                {
                    "hold_status": _("Success"),
                    "description": "successfully hold bance",
                },
                status=status.HTTP_200_OK,
            )
        except (ValidationError, ValueError, Exception) as e:
            if len(serializer.errors) > 0:
                failure_message = serializer.errors
            elif e.args[0] == NOT_ENOUGH_BALANCE_MSG:
                failure_message = NOT_ENOUGH_BALANCE_MSG
            else:
                failure_message = INTERNAL_ERROR_MSG
            return Response(
                {
                    "hold_status": _("failed"),
                    "description": failure_message,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
