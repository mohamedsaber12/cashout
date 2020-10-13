# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.db.models import Q
from django.utils.translation import ugettext as _
from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope, permissions
from rest_framework import status, views
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from disbursement.models import BankTransaction
from utilities.logging import logging_message

from ...models import InstantTransaction
from ..mixins import APIViewPaginatorMixin, IsInstantAPICheckerUser
from ..serializers import (BankTransactionResponseModelSerializer,
                           BulkInstantTransactionReadSerializer,
                           InstantTransactionResponseModelSerializer)


BULK_TRX_INQUIRY_LOGGER = logging.getLogger("instant_bulk_trx_inquiry")

INTERNAL_ERROR_MSG = _("Process stopped during an internal error, can you try again or contact your support team.")


class BulkTransactionInquiryAPIView(APIViewPaginatorMixin, views.APIView):
    """
    Retrieves list of instant transaction objects based on the read serializer input of uuid list
    """

    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope, IsInstantAPICheckerUser]
    throttle_classes = [UserRateThrottle]
    read_serializer = BulkInstantTransactionReadSerializer
    instant_trx_write_serializer = InstantTransactionResponseModelSerializer
    bank_trx_write_serializer = BankTransactionResponseModelSerializer

    def list(self, request, serializer, *args, **kwargs):
        """
        Serializes response of instant transaction objects list
        """
        if serializer.validated_data["bank_transactions"]:
            write_serializer = self.bank_trx_write_serializer
            queryset = BankTransaction.objects.filter(user_created=request.user).\
                filter(~Q(creditor_bank__in=["THWL", "MIDG"])).\
                filter(Q(parent_transaction__transaction_id__in=self.kwargs["trx_ids_list"])).\
                order_by("parent_transaction__transaction_id", "-id").distinct("parent_transaction__transaction_id")

        else:
            write_serializer = self.instant_trx_write_serializer
            queryset = InstantTransaction.objects.filter(from_user=request.user).\
                filter(Q(uid__in=self.kwargs["trx_ids_list"]))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = write_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = write_serializer(queryset, many=True)
        return Response(serializer.data)

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests to retrieve list of detailed instant transactions corresponding to the uuid inputs
        """
        serializer = self.read_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            self.kwargs["trx_ids_list"] = [record for record in serializer.validated_data["transactions_ids_list"]]
            logging_message(
                    BULK_TRX_INQUIRY_LOGGER, "[request] [PASSED UUIDS LIST]", request, f"{serializer.validated_data}"
            )
            return self.list(request, serializer, *args, **kwargs)

        except ValidationError:
            logging_message(
                    BULK_TRX_INQUIRY_LOGGER, "[message] [VALIDATION ERROR]", request, f"{serializer.errors}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as err:
            logging_message(BULK_TRX_INQUIRY_LOGGER, "[message] [GENERAL ERROR]", request, f"{err.args}")
            return Response({"Internal Error": INTERNAL_ERROR_MSG}, status=status.HTTP_424_FAILED_DEPENDENCY)
