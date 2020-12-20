# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import Q
from django.views.generic import ListView

from disbursement.models import BankTransaction

from .mixins import IntegrationUserPassesTestMixin
from .models import InstantTransaction


class BaseInstantTransactionsListView(ListView):
    """
    Base list view for instant transactions
    """

    model = InstantTransaction
    context_object_name = 'instant_transactions'
    paginate_by = 11


class InstantTransactionsListView(IntegrationUserPassesTestMixin, BaseInstantTransactionsListView):
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
                    Q(transaction_status_description__icontains=search_keys)
            )

        return queryset


class BankTransactionsListView(IntegrationUserPassesTestMixin, ListView):
    """
    View for displaying bank transactions
    """

    model = BankTransaction
    context_object_name = 'bank_transactions'
    paginate_by = 11
    template_name = 'instant_cashin/instant_viewer.html'
    queryset = BankTransaction.objects.all()

    def get_queryset(self):
        bank_trx_ids = super().get_queryset().filter(user_created__hierarchy=self.request.user.hierarchy).\
            filter(~Q(creditor_bank__in=["THWL", "MIDG"])).\
            order_by("parent_transaction__transaction_id", "-id").distinct("parent_transaction__transaction_id").\
            values_list("id", flat=True)
        queryset = BankTransaction.objects.filter(id__in=bank_trx_ids).order_by("-created_at")

        if self.request.GET.get('search'):                      # Handle search keywords if any
            search_keys = self.request.GET.get('search')
            queryset.filter(~Q(creditor_bank__in=["THWL", "MIDG"])).filter(
                    Q(parent_transaction__transaction_id__in=search_keys)|
                    Q(creditor_account_number__in=search_keys)|
                    Q(creditor_bank__in=search_keys)
            ).prefetch_related("children_transactions").distinct().order_by("-created_at")

        return queryset
