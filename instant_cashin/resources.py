# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime as dt

from import_export import resources
from import_export.fields import Field

from django.db.models import Q

from core.models import AbstractBaseStatus

from .models import AbstractBaseIssuer, InstantTransaction


class PendingOrangeInstantTransactionsModelResource(resources.ModelResource):
    """
    Generates resource out of instant transactions queryset which filtered based on the provided raw_date
    """

    blank_field = Field()

    class Meta:
        model = InstantTransaction
        fields = ['anon_recipient', 'amount', 'blank_field', 'blank_field', 'blank_field', 'blank_field']
        export_order = ['anon_recipient', 'amount', 'blank_field', 'blank_field', 'blank_field', 'blank_field']

    def __init__(self, user, raw_date):
        """Instantiate resource along with request and raw_date provided"""
        self.user = user
        if len(str(raw_date).split('.')) == 2:
            self.from_date = dt.strptime(raw_date, '%b. %d, %Y').date()
        else:
            self.from_date = dt.strptime(raw_date, '%b %d, %Y').date()

    def get_export_headers(self):
        """Headers of the final exported resource"""
        return ['Mobile Number*', 'Amount*', 'First Name', 'Last Name', 'Id Number', 'Remarks']

    def get_queryset(self):
        """Queryset used to create the resource being exported"""
        queryset = InstantTransaction.objects.filter(
                Q(from_user__hierarchy=self.user.hierarchy) &
                Q(issuer_type=AbstractBaseIssuer.ORANGE) &
                Q(status=AbstractBaseStatus.PENDING) &
                Q(created_at__date=self.from_date)
        )

        return queryset

    def export_resource(self, obj):
        """Export the resource itself to be saved to the disk to a file"""
        obj_resources = super().export_resource(obj)
        return obj_resources
