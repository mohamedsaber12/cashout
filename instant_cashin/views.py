# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import datetime

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.views.generic import ListView

from disbursement.models import BankTransaction

from .mixins import IntegrationUserAndSupportUserPassesTestMixin
from .models import InstantTransaction
from django.core.paginator import Paginator
from data.tasks import ExportDashboardUserTransactionsEwallets, ExportDashboardUserTransactionsBanks



class InstantTransactionsListView(IntegrationUserAndSupportUserPassesTestMixin, ListView):
    """
    View for displaying instant transactions
    """

    model = InstantTransaction
    context_object_name = 'instant_transactions'
    # paginate_by = 11
    template_name = 'instant_cashin/instant_viewer.html'
    queryset = InstantTransaction.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['admin'] = self.request.GET.get('client')
        return context

    def get_queryset(self):
        client_username_query_parameter = self.request.GET.get('client')
        if self.request.user.is_support and client_username_query_parameter:
            user = get_object_or_404(get_user_model(), username=client_username_query_parameter)
            hierarchy_to_filter_with = user.hierarchy
        else:
            hierarchy_to_filter_with = self.request.user.hierarchy
        queryset = super().get_queryset().filter(
            from_user__hierarchy=hierarchy_to_filter_with
        ).order_by("-created_at")
                    
        if self.request.GET.get('search'):                      # Handle search keywords if any
            search_keys = self.request.GET.get('search')
            queryset = queryset.filter(
                Q(uid__iexact=search_keys)|
                Q(anon_recipient__iexact=search_keys)|
                Q(transaction_status_description__icontains=search_keys)
            )
        if self.request.GET.get('export_start_date') and self.request.GET.get('export_end_date'):
            queryset = queryset.filter(updated_at__gte=self.request.GET.get('export_start_date'),
                                       updated_at__lte=self.request.GET.get('export_end_date'))
            return queryset
        paginator = Paginator(queryset, 20)
        page = self.request.GET.get('page')
        return paginator.get_page(page)
        
    def get(self, request):
        export_start_date = request.GET.get('export_start_date')
        export_end_date = request.GET.get('export_end_date')
        if export_start_date and export_end_date:
            EXPORT_MESSAGE = f"Please check your mail for report {request.user.email}"
            uids = self.get_queryset().values_list("uid", flat=True)
            print(uids)
            ExportDashboardUserTransactionsEwallets.delay(request.user.id,list(uids),export_start_date, export_end_date )
            return HttpResponseRedirect(f"{self.request.path}?export_message={EXPORT_MESSAGE}")
        else:
            return super().get(self,request)



class BankTransactionsListView(IntegrationUserAndSupportUserPassesTestMixin, ListView):
    """
    View for displaying bank transactions
    """

    model = BankTransaction
    context_object_name = 'bank_transactions'
    # paginate_by = 11
    template_name = 'instant_cashin/instant_viewer.html'
    queryset = BankTransaction.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['admin'] = self.request.GET.get('client')
        context['is_bank_transactions'] = 'yes'
        return context

    def get_queryset(self):
        client_username_query_parameter = self.request.GET.get('client')
        if self.request.user.is_support and client_username_query_parameter:
            user = get_object_or_404(get_user_model(), username=client_username_query_parameter)
            hierarchy_to_filter_with = user.hierarchy
        else:
            hierarchy_to_filter_with = self.request.user.hierarchy
        bank_trx_ids = super().get_queryset().filter(user_created__hierarchy=hierarchy_to_filter_with).\
            filter(~Q(creditor_bank__in=["THWL", "MIDG"])).\
            order_by("parent_transaction__transaction_id", "-id").distinct("parent_transaction__transaction_id").\
            values_list("id", flat=True)
        queryset = BankTransaction.objects.filter(id__in=bank_trx_ids).order_by("-created_at")

        if self.request.GET.get('search'):                      # Handle search keywords if any
            search_keys = self.request.GET.get('search')
            queryset = queryset.filter(~Q(creditor_bank__in=["THWL", "MIDG"])).filter(
                    Q(parent_transaction__transaction_id__iexact=search_keys)|
                    Q(creditor_account_number__in=search_keys)|
                    Q(creditor_bank__in=search_keys)
            ).prefetch_related("children_transactions").distinct().order_by("-created_at")
            
        if self.request.GET.get('export_start_date') and self.request.GET.get('export_end_date'):
            queryset = queryset.filter(updated_at__gte=self.request.GET.get('export_start_date'),
                                       updated_at__lte=self.request.GET.get('export_end_date'))
            return queryset
            
        paginator = Paginator(queryset, 20)
        page = self.request.GET.get('page')
        return paginator.get_page(page)
        
    def get(self, request):
        export_start_date = request.GET.get('export_start_date')
        export_end_date = request.GET.get('export_end_date')
        if export_start_date and export_end_date:
            EXPORT_MESSAGE = f"Please check your mail for report {request.user.email}"
            ExportDashboardUserTransactionsBanks.delay(self.request.user.id, list(self.get_queryset().values_list("id", flat=True)),export_start_date, export_end_date )
            return HttpResponseRedirect(f"{self.request.path}?export_message={EXPORT_MESSAGE}")
        else:
            return super().get(self,request)

