# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from django.conf import settings
from django.db.models import Count, Q
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from core.models import AbstractBaseStatus

from .mixins import RootFromInstantFamilyRequiredMixin
from .models import AbstractBaseIssuer, InstantTransaction
from .tasks import generate_pending_orange_instant_transactions


class PendingOrangeInstantTransactionsListView(RootFromInstantFamilyRequiredMixin, ListView):
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


class DownloadPendingOrangeInstantTransactionsView(RootFromInstantFamilyRequiredMixin, View):
    """
    Downloads sheet with the pending Orange Transactions of the provided date
    """

    def get(self, request, *args, **kwargs):
        """Handles coming Ajax calls to download the sheet"""
        if request.is_ajax() and request.GET.get('date'):
            raw_date = request.GET.get('date')
            generate_pending_orange_instant_transactions.delay(request.user.username, raw_date)
            # ToDo: Logging
            return HttpResponseRedirect(reverse('instant_cashin:home'))

        raise Http404
