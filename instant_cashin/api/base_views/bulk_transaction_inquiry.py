# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import Q
from django.utils.translation import ugettext as _

from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope, permissions
from rest_framework import status, views
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from ...models import InstantTransaction
from ..mixins import IsInstantAPICheckerUser
from ..serializers import BulkInstantTransactionReadSerializer, InstantTransactionWriteModelSerializer


INTERNAL_ERROR_MSG = _("Process stopped during an internal error, can you try again or contact your support team.")


class BulkTransactionInquiryAPIView(views.APIView):
    """
    Retrieves list of instant transaction objects based on the read serializer input of uuid list
    """

    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope, IsInstantAPICheckerUser]
    throttle_classes = [UserRateThrottle]
    read_serializer = BulkInstantTransactionReadSerializer
    write_serializer = InstantTransactionWriteModelSerializer

    def list(self, request, *args, **kwargs):
        """Serializes response of instant transaction objects list"""
        queryset = InstantTransaction.objects.filter(from_user=request.user).filter(
                Q(uid__in=self.kwargs["trx_ids_list"])
        )

        # page = self.paginate_queryset(queryset)
        # if page is not None:
        #     serializer = self.get_serializer(page, many=True)
        #     return self.get_paginated_response(serializer.data)

        serializer = self.write_serializer(queryset, many=True)
        return Response(serializer.data)

    def get(self, request, *args, **kwargs):
        """Handles GET requests to retrieve list of detailed instant transactions corresponding to the uuid inputs"""
        serializer = self.read_serializer(data=request.data)

        try:
            # ToDo: Logging
            serializer.is_valid(raise_exception=True)
            self.kwargs["trx_ids_list"] = [record for record in serializer.validated_data['transactions_ids_list']]
            return self.list(request, *args, **kwargs)

        except ValidationError as err:
            # ToDo: Logging
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as err:
            # ToDo: Logging, using err.args[0]
            return Response({"Internal Error": INTERNAL_ERROR_MSG}, status=status.HTTP_424_FAILED_DEPENDENCY)
