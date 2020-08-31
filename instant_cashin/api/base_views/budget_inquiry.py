# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import gettext as _

from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope, permissions
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from utilities.functions import custom_budget_logger

from ..mixins import IsInstantAPICheckerUser


INTERNAL_ERROR_MSG = _("Process stopped during an internal error, can you try again or contact your support team.")
EXTERNAL_ERROR_MSG = _("Process stopped during an external error, can you try again or contact your support team.")


class BudgetInquiryAPIView(views.APIView):
    """
    Handles custom budget inquiries from the disbursers
    """

    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope, IsInstantAPICheckerUser]
    throttle_classes = [UserRateThrottle]

    def get(self, request, *args, **kwargs):
        """Handles GET requests of the budget inquiry api view"""
        disburser = request.user.root

        if not disburser.has_custom_budget:
            custom_budget_logger(
                    disburser, f"Internal Error: This user has no custom budget configurations",
                    disburser, head="[CUSTOM BUDGET - API INQUIRY]"
            )
            return Response({'Internal Error': INTERNAL_ERROR_MSG}, status=status.HTTP_404_NOT_FOUND)

        budget = disburser.budget.current_balance
        custom_budget_logger(
                disburser, f"Current budget: {budget} LE", disburser, head="[CUSTOM BUDGET - API INQUIRY]"
        )

        return Response({'current_budget': f"Your current budget is {budget} LE"}, status=status.HTTP_200_OK)
