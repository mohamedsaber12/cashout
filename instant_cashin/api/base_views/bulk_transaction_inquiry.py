# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import Q

from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope, permissions
from rest_framework import status, views
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from ...models import InstantTransaction
from ..mixins import IsInstantAPICheckerUser
from ..serializers import BulkInstantTransactionReadSerializer, InstantTransactionWriteModelSerializer


class BulkTransactionInquiryAPIView(views.APIView):
    """
    """

    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope, IsInstantAPICheckerUser]
    throttle_classes = [UserRateThrottle]
    read_serializer = BulkInstantTransactionReadSerializer
    write_serializer = InstantTransactionWriteModelSerializer

    def list(self, request, *args, **kwargs):
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
        serializer = self.read_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            self.kwargs["trx_ids_list"] = [record['transaction_id'] for record in serializer.validated_data['ids_list']]
            return self.list(request, *args, **kwargs)

        except ValidationError:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
