# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import random
import array

from django.contrib.auth.models import Permission
from django.db.models import Q
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.translation import ugettext as _
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView
from django.core.paginator import Paginator

from instant_cashin.utils import get_from_env
from data.models import Doc
from utilities.models import Budget, CallWalletsModerator, FeeSetup
from utilities.logging import logging_message
from disbursement.views import DisbursementDocTransactionsView
from disbursement.models import BankTransaction
from oauth2_provider.models import Application
from ..forms import SupportUserCreationForm, OnboardingApiClientForm
from ..mixins import (
    SuperRequiredMixin, SupportUserRequiredMixin, SupportOrRootOrMakerUserPassesTestMixin,
)
from ..models import (
    Client, SupportSetup, SupportUser, RootUser, SuperAdminUser, User, Setup,
    EntitySetup, InstantAPIViewerUser, InstantAPICheckerUser
)

ROOT_CREATE_LOGGER = logging.getLogger("root_create")

DIGITS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
LOCASE_CHARACTERS = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h',
                     'i', 'j', 'k', 'm', 'n', 'o', 'p', 'q',
                     'r', 's', 't', 'u', 'v', 'w', 'x', 'y',
                     'z']
UPCASE_CHARACTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
                     'I', 'J', 'K', 'M', 'N', 'O', 'p', 'Q',
                     'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y',
                     'Z']
SYMBOLS = ['#']
# combines all the character arrays above to form one array
COMBINED_LIST = DIGITS + UPCASE_CHARACTERS + LOCASE_CHARACTERS + SYMBOLS

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
        if self.request.GET.get('status') and self.request.GET.get('status') == 'P':
            if doc_obj.is_e_wallet:
                doc_transactions = doc_transactions.filter(
                    is_disbursed=False, reason=''
                )


        # add server side pagination
        paginator = Paginator(doc_transactions, 10)
        page = self.request.GET.get('page', 1)
        queryset = paginator.get_page(page)

        context = {
            'request_full_path': request.get_full_path(),
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


class OnboardingNewInstantAdmin(SupportUserRequiredMixin, View):
    """
    List/Create view for onboarding new client over the integration patch
    """

    model = Client
    context_object_name = 'clients'
    template_name = 'support/integration_client_credentials.html'

    def define_new_admin_hierarchy(self, new_user):
        """
        Generate/Define the hierarchy of the new admin user
        :param new_user: the new admin user to be created
        :return: the new admin user with its new hierarchy
        """
        maximum = max(RootUser.objects.values_list('hierarchy', flat=True), default=False)
        maximum = 0 if not maximum else maximum

        try:
            new_user.hierarchy = maximum + 1
        except TypeError:
            new_user.hierarchy = 1

        return new_user

    def generate_strong_password(self, pass_length):
        # randomly select at least one character from each character set above
        rand_digit = random.choice(DIGITS)
        rand_upper = random.choice(UPCASE_CHARACTERS)
        rand_lower = random.choice(LOCASE_CHARACTERS)
        rand_symbol = random.choice(SYMBOLS)

        # combine the character randomly selected above
        temp_pass = rand_digit + rand_upper + rand_lower + rand_symbol
        temp_pass_list = []
        for x in range(pass_length - 4):
            temp_pass = temp_pass + random.choice(COMBINED_LIST)
            temp_pass_list = array.array('u', temp_pass)
            random.shuffle(temp_pass_list)

        return ''.join(temp_pass_list)

    def get_queryset(self):
        creator = self.request.user.my_setups.user_created
        all_super_admins = [creator]

        # get all super admins that has same permission
        if creator.is_instant_model_onboarding:
            all_super_admins = [x for x in SuperAdminUser.objects.all() if x.is_instant_model_onboarding]
        qs = Client.objects.filter(creator__in=all_super_admins).order_by('-id')

        if self.request.GET.get('search'):
            search_key = self.request.GET.get('search')
            return qs.filter(Q(client__username__icontains=search_key) |
                             Q(client__mobile_no__icontains=search_key) |
                             Q(client__email__icontains=search_key)).order_by('-id')

        return qs

    def get(self, request, *args, **kwargs):
        """Handles GET requests for credentials list view"""
        context = {
            'form': OnboardingApiClientForm(),
            'clients': self.get_queryset(),
            "is_production": get_from_env("ENVIRONMENT") == 'production',
        }

        return render(request, template_name=self.template_name, context=context)

    def post(self, request, *args, **kwargs):
        """Handles POST requests to onboard new client"""
        context = {
            'form': OnboardingApiClientForm(request.POST),
            'clients': self.get_queryset(),
            "is_production": get_from_env("ENVIRONMENT") == 'production',
            'show_add_form': True
        }

        if context['form'].is_valid():
            form = context['form']
            try:
                data = form.cleaned_data
                client_name = data['client_name'].strip().lower().replace(" ", "_")
                # create root
                root = RootUser.objects.create(
                    username=f"{client_name}_integration_admin",
                    email=f"{client_name}_integration_admin@paymob.com",
                    user_type=3
                )

                # set root password
                root.set_password(get_from_env('INSTANT_ADMIN_DEFAULT_PASSWORD'))
                # set admin hierarchy
                root = self.define_new_admin_hierarchy(root)
                # add root field when create root
                root.root = root
                root.save()

                # add permissions
                root.user_permissions.add(
                    Permission.objects.get(content_type__app_label='users', codename='instant_model_onboarding'),
                    Permission.objects.get(content_type__app_label='users', codename='has_instant_disbursement')
                )

                # start create extra setup
                entity_dict = {
                    "user": self.request.user.my_setups.user_created,
                    "entity": root,
                    "agents_setup": True,
                    "fees_setup": True
                }
                client_dict = {
                    "creator": self.request.user.my_setups.user_created,
                    "client": root,
                }

                Setup.objects.create(
                    user=root, pin_setup=True, levels_setup=True,
                    maker_setup=True, checker_setup=True, category_setup=True
                )
                CallWalletsModerator.objects.create(
                    user_created=root, disbursement=False, change_profile=False,
                    set_pin=False, user_inquiry=False, balance_inquiry=False
                )
                root.user_permissions. \
                    add(Permission.objects.get(content_type__app_label='users', codename='has_disbursement'))

                EntitySetup.objects.create(**entity_dict)
                Client.objects.create(**client_dict)
                # finish create extra setup

                msg = f"New Root/Admin created with username: {root.username} by {request.user.username}"
                logging_message(ROOT_CREATE_LOGGER, "[message] [NEW ADMIN CREATED]", self.request, msg)

                # handle budget and fees setup
                root_budget = Budget.objects.create(
                    disburser=root, created_by=self.request.user, current_balance=2000
                )

                FeeSetup.objects.create(budget_related=root_budget, issuer='vf',
                    fee_type='p', percentage_value=2.25)
                FeeSetup.objects.create(budget_related=root_budget, issuer='es',
                    fee_type='p', percentage_value=2.25)
                FeeSetup.objects.create(budget_related=root_budget, issuer='og',
                    fee_type='p', percentage_value=2.25)
                FeeSetup.objects.create(budget_related=root_budget, issuer='bw',
                    fee_type='p', percentage_value=2.25)
                FeeSetup.objects.create(budget_related=root_budget, issuer='am',
                    fee_type='p', percentage_value=3.0)
                FeeSetup.objects.create(budget_related=root_budget, issuer='bc',
                    fee_type='f', fixed_value=20)

                # create dashboard user
                dashboard_user = InstantAPIViewerUser.objects.create(
                    username=f"{client_name}_dashboard_user",
                    email=f"{client_name}_dashboard_user@{client_name}.com",
                    user_type=7,
                    root=root,
                    hierarchy=root.hierarchy
                )
                # generate strong password for dashboard user
                dashboard_user_pass = self.generate_strong_password(25)
                dashboard_user.set_password(dashboard_user_pass)
                dashboard_user.save()

                # create api checker
                api_checker = InstantAPICheckerUser.objects.create(
                    username=f"{client_name}_api_checker",
                    email=f"{client_name}_api_checker@{client_name}.com",
                    user_type=6,
                    root=root,
                    hierarchy=root.hierarchy
                )

                # generate strong password for api checker
                api_checker_pass = self.generate_strong_password(25)
                api_checker.set_password(api_checker_pass)
                api_checker.save()

                # create oauth2 provider app
                oauth2_app = Application.objects.create(
                    client_type=Application.CLIENT_CONFIDENTIAL, authorization_grant_type=Application.GRANT_PASSWORD,
                    name=f"{api_checker.username} OAuth App", user=api_checker
                )

                # add permissions
                onboarding_permission = Permission.objects.get(
                    content_type__app_label='users', codename='instant_model_onboarding')
                api_docs_permission = Permission.objects.get(
                    content_type__app_label='users', codename='can_view_api_docs')

                dashboard_user.user_permissions.add(onboarding_permission)

                api_checker.user_permissions.add(onboarding_permission, api_docs_permission)

                context = {
                    'form': OnboardingApiClientForm(),
                    'clients': self.get_queryset(),
                    "is_production": get_from_env("ENVIRONMENT") == 'production',
                    "has_error": 'No',
                    "credentials_data": {
                        "dashboard_user": {
                            "username": dashboard_user.username,
                            "password": dashboard_user_pass
                        },
                        "api_checker": {
                            "username": api_checker.username,
                            "password": api_checker_pass,
                            "client_id": oauth2_app.client_id,
                            "client_secret": oauth2_app.client_secret
                        }
                    }
                }
            except Exception as err:
                print(err)
                error_msg = "Process stopped during an internal error, please can you try again."
                error = {
                    "message": error_msg
                }
                context["has_error"]= True
                context['error'] = error
        return render(request, template_name=self.template_name, context=context)


class ClientCredentialsDetails(SupportUserRequiredMixin, View):

    """
    Detail view to retrieve Credentials for client
    """

    def dispatch(self, request, *args, **kwargs):
        """Shared attributes between GET and POST methods"""
        self.client_id = self.kwargs['client_id']
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        """Handle GET request to retrieve Credentials for specific Client with id"""

        client = Client.objects.filter(id=self.client_id)

        if not client.exists():
            raise Http404(_(f"Client with id: {self.client_id} not found."))

        client_obj = client.first()
        users = User.objects.filter(root=client_obj.client)
        dashboard_users = users.filter(user_type=7)
        api_checkers = users.filter(user_type=6)
        for ch in api_checkers:
            ch.auth_obj = Application.objects.get(user__username=ch.username)
        context = {
            "client": client_obj,
            "dashboard_users": dashboard_users,
            "api_checkers": api_checkers,
        }

        return render(request, 'support/client_Credentials_details.html', context=context)