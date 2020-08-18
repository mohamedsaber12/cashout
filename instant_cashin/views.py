# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os

from django.conf import settings
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from core.models import AbstractBaseStatus
from utilities.constants import SPREADSHEET_CONTENT_TYPE_CONSTANT
from utilities.logging import logging_message

from .mixins import InstantReviewerRequiredMixin, RootWithInstantPermissionsPassesTestMixin, RootOwnsRequestedFileTestMixin
from .models import AbstractBaseIssuer, InstantTransaction
from .tasks import generate_pending_orange_instant_transactions


GENERATE_SHEET_LOGGER = logging.getLogger("generate_sheet")
DOWNLOAD_SERVE_LOGGER = logging.getLogger("download_serve")


class BaseInstantTransactionsListView(ListView):
    """
    Base list view for instant transactions
    """

    model = InstantTransaction
    context_object_name = 'instant_transactions'
    paginate_by = 11


class InstantTransactionsListView(InstantReviewerRequiredMixin, BaseInstantTransactionsListView):
    """
    View for displaying instant transactions
    """

    template_name = 'instant_cashin/instant_viewer.html'
    queryset = InstantTransaction.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset().filter(from_user__hierarchy=self.request.user.hierarchy)

        if self.request.GET.get('search'):                      # Handle search keywords if any
            search_keys = self.request.GET.get('search')
            queryset.filter(
                    Q(uid__iexact=search_keys)|
                    Q(anon_recipient__iexact=search_keys)|
                    Q(failure_reason__icontains=search_keys)
            )

        return queryset


class PendingOrangeInstantTransactionsListView(RootWithInstantPermissionsPassesTestMixin,
                                               BaseInstantTransactionsListView):
    """
    Home view for Admin users that belong to instant disbursement family, Lists all of the pending
    Orange instant transactions aggregated per every day.
    """

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


class DownloadPendingOrangeInstantTransactionsView(RootWithInstantPermissionsPassesTestMixin, View):
    """
    Downloads sheet with the pending Orange Transactions of the provided date
    """

    def get(self, request, *args, **kwargs):
        """Handles coming Ajax calls to download the sheet"""
        if request.is_ajax() and request.GET.get('date'):
            raw_date = request.GET.get('date')
            generate_pending_orange_instant_transactions.delay(request.user.username, raw_date)
            logging_message(
                    GENERATE_SHEET_LOGGER, "[PENDING ORANGE INSTANT TRANSACTIONS - GENERATED SUCCESSFULLY]", request,
                    f"Sheet generated with instant transactions occurred at: {raw_date}"
            )
            return HttpResponseRedirect(reverse('instant_cashin:pending_list'))

        logging_message(
                GENERATE_SHEET_LOGGER, "[PENDING ORANGE INSTANT TRANSACTIONS - GENERATE ERROR]", request,
                f"Raw request: {vars(request)}"
        )
        raise Http404


class ServeDownloadingInstantTransactionsView(RootWithInstantPermissionsPassesTestMixin,
                                              RootOwnsRequestedFileTestMixin,
                                              View):
    """
    Serve downloading instant transactions sheet
    """

    def get(self, request, *args, **kwargs):
        """Handles GET requests to serve downloading of the file via the response"""
        filename = request.GET.get('filename', None)

        if filename:
            file_path = f"{settings.MEDIA_ROOT}/documents/instant_transactions/{filename}"

            if os.path.exists(file_path):

                with open(file_path, 'rb') as fh:
                    response = HttpResponse(fh.read(), content_type=SPREADSHEET_CONTENT_TYPE_CONSTANT)
                    response['Content-Disposition'] = f"attachment; filename={filename}"
                    logging_message(
                            DOWNLOAD_SERVE_LOGGER, "[PENDING ORANGE INSTANT TRANSACTIONS - SHEET DOWNLOAD]", request,
                            f"File name: {filename}"
                    )
                    return response

        logging_message(
                DOWNLOAD_SERVE_LOGGER, "[PENDING ORANGE INSTANT TRANSACTIONS - ERROR SHEET DOWNLOAD]", request,
                f"Raw Request: {vars(request)}"
        )
        raise Http404
