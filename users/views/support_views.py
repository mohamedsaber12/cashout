# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import Q
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import ugettext as _
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView
from django.core.paginator import Paginator

from data.models import Doc
from disbursement.views import DisbursementDocTransactionsView
from disbursement.utils import add_fees_and_vat_to_qs
from disbursement.models import BankTransaction

from ..forms import SupportUserCreationForm
from ..mixins import (
    SuperRequiredMixin, SupportUserRequiredMixin, SupportOrRootOrMakerUserPassesTestMixin,
)
from ..models import Client, SupportSetup, SupportUser, RootUser, SuperAdminUser


class SuperAdminSupportSetupCreateView(SuperRequiredMixin, CreateView):
    """
    Create view for super admin users to create support users
    """

    model = SupportUser
    form_class = SupportUserCreationForm
    template_name = 'support/add_support.html'
    success_url = reverse_lazy('users:support')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        self.support_user = form.save()
        support_setup_dict = {
            'support_user': self.support_user,
            'user_created': self.request.user
        }
        SupportSetup.objects.create(**support_setup_dict)

        return HttpResponseRedirect(self.success_url)


class SupportUsersListView(SuperRequiredMixin, ListView):
    """
    List support users related to the currently logged in super admin
    Search for support users by username, email or mobile no by "search" query parameter.
    """

    model = SupportSetup
    paginate_by = 6
    context_object_name = 'supporters'
    template_name = 'support/list.html'

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(user_created=self.request.user)

        if self.request.GET.get("search"):
            search = self.request.GET.get("search")
            return qs.filter(Q(support_user__username__icontains=search) |
                             Q(support_user__email__icontains=search) |
                             Q(support_user__mobile_no__icontains=search))

        return qs


class SupportHomeView(SupportUserRequiredMixin, TemplateView):
    """
    Template view for support users home page
    """

    template_name = 'support/home.html'


class ClientsForSupportListView(SupportUserRequiredMixin, ListView):
    """
    List view for retrieving all clients users to the support user
    """

    model = Client
    # paginate_by = 6
    context_object_name = 'clients'
    template_name = 'support/clients.html'

    def get_queryset(self):
        qs = super().get_queryset()
        creator = self.request.user.my_setups.user_created
        all_super_admins = [creator]

        # get all super admins that has same permission
        if creator.is_vodafone_default_onboarding:
            all_super_admins = [x for x in SuperAdminUser.objects.all() if x.is_vodafone_default_onboarding]
        elif creator.is_instant_model_onboarding:
            all_super_admins = [x for x in SuperAdminUser.objects.all() if x.is_instant_model_onboarding]
        elif creator.is_accept_vodafone_onboarding:
            all_super_admins = [x for x in SuperAdminUser.objects.all() if x.is_accept_vodafone_onboarding]
        elif creator.is_vodafone_facilitator_onboarding:
            all_super_admins = [x for x in SuperAdminUser.objects.all() if x.is_vodafone_facilitator_onboarding]
        elif creator.is_banks_standard_model_onboaring:
            all_super_admins = [x for x in SuperAdminUser.objects.all() if x.is_banks_standard_model_onboaring]

        qs = qs.filter(creator__in=all_super_admins)

        if self.request.GET.get('search'):
            search_key = self.request.GET.get('search')
            return qs.filter(Q(client__username__icontains=search_key) |
                             Q(client__mobile_no__icontains=search_key) |
                             Q(client__email__icontains=search_key))

        return qs


class DocumentsForSupportListView(SupportUserRequiredMixin,
                                  SupportOrRootOrMakerUserPassesTestMixin,
                                  ListView):
    """
    Lists disbursement documents uploaded by specific Admin's members.
    """

    model = Doc
    paginate_by = 10
    context_object_name = 'documents'
    template_name = 'support/documents_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['admin'] = self.kwargs['username']
        return context

    def get_queryset(self, queryset=None):
        admin = RootUser.objects.get(username=self.kwargs['username'])
        qs = Doc.objects.filter(owner__hierarchy=admin.hierarchy).prefetch_related('disbursement_txn')

        if self.request.GET.get('search'):
            doc_id = self.request.GET.get('search')
            qs = qs.filter(id__icontains=doc_id)

        return qs


class DocumentForSupportDetailView(SupportUserRequiredMixin,
                                   SupportOrRootOrMakerUserPassesTestMixin,
                                   View):
    """
    Detail view to retrieve every little detail about every document
    """

    def retrieve_doc_status(self, doc_obj):
        """Retrieve doc status given doc object"""

        if doc_obj.validation_process_is_running:
            return _('Validation process is running')
        elif doc_obj.validated_successfully:
            return _('Validated successfully')
        elif doc_obj.validation_failed:
            return _('Validation failure')
        elif doc_obj.disbursement_failed:
            return _('Disbursement failure')
        elif doc_obj.waiting_disbursement:
            return _('Ready for disbursement')
        elif doc_obj.waiting_disbursement_callback:
            return _('Disbursed successfully and waiting for the disbursement callback')
        elif doc_obj.disbursed_successfully:
            return _('Disbursed successfully')

    def dispatch(self, request, *args, **kwargs):
        """Shared attributes between GET and POST methods"""
        self.doc_id = self.kwargs['doc_id']
        self.admin_username = self.kwargs['username']
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Handle GET request to retrieve details for specific document with id"""

        # ToDo: Should handle different types of files, NOW it ONLY handles e-wallets files -disbursement_data-
        admin = RootUser.objects.get(username=self.admin_username)
        doc = Doc.objects.prefetch_related('disbursement_data', 'disbursement_txn', 'reviews').filter(
                id=self.doc_id, owner__hierarchy=admin.hierarchy
        )

        if not doc.exists():
            raise Http404(_(f"Document with id: {self.doc_id} for {self.admin_username} entity members not found."))

        doc_obj = doc.first()
        doc_transactions = doc_obj.disbursement_data.all()
        doc_transactions_qs = doc_obj.disbursement_data.all()
        search_filter = None
        if self.request.GET.get('search'):
            search_keys = self.request.GET.get('search')
            search_filter = (
                Q(msisdn__icontains=search_keys)|
                Q(id__iexact=search_keys)
            )
        if doc_obj.is_bank_wallet:
            doc_transactions = doc_obj.bank_wallets_transactions.all()
            doc_transactions_qs = doc_obj.bank_wallets_transactions.all()
            if search_filter:
                search_filter = (
                    Q(uid__iexact=search_keys)|
                    Q(anon_recipient__icontains=search_keys)|
                    Q(transaction_status_description__icontains=search_keys)
                )
        elif doc_obj.is_bank_card:
            doc_transactions = doc_obj.bank_cards_transactions.all()\
                .order_by('parent_transaction__transaction_id', '-created_at')\
                .distinct('parent_transaction__transaction_id')
            doc_transactions_qs = BankTransaction.objects.filter(
                id__in=doc_transactions.values('id')
            )
            if search_filter:
                search_filter = (
                    Q(parent_transaction__transaction_id__iexact=search_keys)|
                    Q(creditor_account_number__icontains=search_keys)|
                    Q(creditor_bank__icontains=search_keys)
                )
        if search_filter:
            doc_transactions = doc_transactions.filter(search_filter)

        # add server side pagination
        paginator = Paginator(doc_transactions, 10)
        page = self.request.GET.get('page', 1)
        queryset = paginator.get_page(page)

        context = {
            'doc_obj': doc_obj,
            'reviews': doc_obj.reviews.all() ,
            'doc_status': self.retrieve_doc_status(doc_obj),
            'disbursement_ratio': doc_obj.disbursement_ratio(),
            'is_reviews_completed': doc_obj.is_reviews_completed(),
            'disbursement_records': queryset,
            'disbursement_doc_data': doc_obj.disbursement_txn,
            'doc_transactions_totals':
                DisbursementDocTransactionsView.get_document_transactions_totals(doc_obj, doc_transactions_qs),
        }

        return render(request, 'support/document_details.html', context=context)
