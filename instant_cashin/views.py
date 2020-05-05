# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import Count, Q
from django.views.generic import ListView

from core.models import AbstractBaseStatus

from .models import AbstractBaseIssuer, InstantTransaction


class PendingOrangeInstantTransactionsListView(ListView):
    """
    Home view for Admin users that belong to instant disbursement family, Lists all of the pending
    Orange instant transactions aggregated per every day.
    """

    model = InstantTransaction
    context_object_name = 'orange_pending_transactions'
    template_name = 'instant_cashin/admin_home.html'

    def get_queryset(self):
        queryset = InstantTransaction.objects.filter(
                Q(from_user__hierarchy=self.request.user.hierarchy) &
                Q(issuer_type=AbstractBaseIssuer.ORANGE) &
                Q(status=AbstractBaseStatus.PENDING)
        )

        dates_qs = queryset.values('created_at__date').annotate(Count('created_at__date'))
        dates_unique_list = set([record['created_at__date'] for record in dates_qs])
        ordered_dates_unique_list = sorted(dates_unique_list, reverse=True)

        # ToDo
        # total_trx_per_day = queryset.filter(created_at__date=ordered_dates_unique_list[0]).annotate(Count('uid'))

        return ordered_dates_unique_list
