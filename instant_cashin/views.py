# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.views.generic import ListView
from django.utils.timezone import datetime, make_aware

from disbursement.models import BankTransaction

from .mixins import IntegrationUserAndSupportUserPassesTestMixin
from .models import InstantTransaction
from django.core.paginator import Paginator


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
        # pagination query string
        query_string = ""
        if self.request.GET.get('client', None):
            query_string += "client=" + self.request.GET.get('client', None)
        context['query_string'] = query_string
        return context

    def get_queryset(self):
        client_username_query_parameter = self.request.GET.get('client')
        if self.request.user.is_support and client_username_query_parameter:
            user = get_object_or_404(get_user_model(), username=client_username_query_parameter)
            hierarchy_to_filter_with = user.hierarchy
        else:
            hierarchy_to_filter_with = self.request.user.hierarchy
        filter_dict = {
            'from_user__hierarchy':hierarchy_to_filter_with,
        }
        # add filters to filter dict
        if self.request.GET.get('number'):
            filter_dict['anon_recipient__contains'] = self.request.GET.get('number')
        if self.request.GET.get('issuer'):
            filter_dict['issuer_type'] = self.request.GET.get('issuer')
        if self.request.GET.get('start_date'):
            start_date = self.request.GET.get('start_date')
            first_day = datetime(
                year=int(start_date.split('-')[0]),
                month=int(start_date.split('-')[1]),
                day=int(start_date.split('-')[2]),
            )
            filter_dict['disbursed_date__gte'] = make_aware(first_day)
        if self.request.GET.get('end_date'):
            end_date = self.request.GET.get('end_date')
            last_day = datetime(
                year=int(end_date.split('-')[0]),
                month=int(end_date.split('-')[1]),
                day=int(end_date.split('-')[2]),
                hour=23,
                minute=59,
                second=59,
            )
            filter_dict['disbursed_date__lte'] = make_aware(last_day)

        queryset = super().get_queryset().filter(**filter_dict).order_by("-created_at")
        paginator = Paginator(queryset, 20)
        page = self.request.GET.get('page', 1)
        return paginator.get_page(page)

    def get(self, request):
        return super().get(self, request)



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
        # pagination query string
        query_string = ""
        if self.request.GET.get('client', None):
            query_string += "client=" + self.request.GET.get('client', None)
        context['query_string'] = query_string
        return context

    def get_queryset(self):
        client_username_query_parameter = self.request.GET.get('client')
        if self.request.user.is_support and client_username_query_parameter:
            user = get_object_or_404(get_user_model(), username=client_username_query_parameter)
            hierarchy_to_filter_with = user.hierarchy
        else:
            hierarchy_to_filter_with = self.request.user.hierarchy

        filter_dict = {
            'user_created__hierarchy': hierarchy_to_filter_with,
        }
        # add filters to filter dict
        if self.request.GET.get('transaction_id'):
            filter_dict['parent_transaction__transaction_id__contains'] = self.request.GET.get('transaction_id')
        if self.request.GET.get('account_number'):
            filter_dict['creditor_account_number__contains'] = self.request.GET.get('account_number')
        if self.request.GET.get('start_date'):
            start_date = self.request.GET.get('start_date')
            first_day = datetime(
                year=int(start_date.split('-')[0]),
                month=int(start_date.split('-')[1]),
                day=int(start_date.split('-')[2]),
            )
            filter_dict['disbursed_date__gte'] = make_aware(first_day)
        if self.request.GET.get('end_date'):
            end_date = self.request.GET.get('end_date')
            last_day = datetime(
                year=int(end_date.split('-')[0]),
                month=int(end_date.split('-')[1]),
                day=int(end_date.split('-')[2]),
                hour=23,
                minute=59,
                second=59,
            )
            filter_dict['disbursed_date__lte'] = make_aware(last_day)

        queryset = super().get_queryset().filter(**filter_dict). \
            filter(~Q(creditor_bank__in=["THWL", "MIDG"])). \
            order_by("parent_transaction__transaction_id", "-id", "-created_at"). \
            distinct("parent_transaction__transaction_id")
        paginator = Paginator(queryset, 20)
        page = self.request.GET.get('page')
        return paginator.get_page(page)

    def get(self, request):
        return super().get(self, request)
