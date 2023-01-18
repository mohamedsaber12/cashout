# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import array
import json
import logging
import random

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView
from oauth2_provider.models import Application
from rest_framework_expiring_authtoken.models import ExpiringToken

from instant_cashin.utils import get_from_env
from users.models.access_token import AccessToken
from users.models.instant_api_checker import InstantAPICheckerUser
from users.models.instant_api_viewer import InstantAPIViewerUser
from utilities.logging import logging_message
from utilities.models import Budget, CallWalletsModerator, FeeSetup

from ..forms import (ClientFeesForm, CreationNewMerchantForm,
                     CustomClientProfilesForm, RootCreationForm)
from ..mixins import (
    DjangoAdminRequiredMixin, OnboardUserRequiredMixin, RootRequiredMixin,
    SuperFinishedSetupMixin, SuperOrOnboardUserRequiredMixin,
    SuperOwnsClientRequiredMixin, SuperOwnsCustomizedBudgetClientRequiredMixin,
    SuperRequiredMixin,
    SuperWithAcceptVFAndVFFacilitatorOnboardingPermissionRequired)
from ..models import Client, EntitySetup, RootUser, Setup, User

SEND_EMAIL_LOGGER = logging.getLogger("send_emails")

ROOT_CREATE_LOGGER = logging.getLogger("root_create")
DELETE_USER_VIEW_LOGGER = logging.getLogger("delete_user_view")
DIGITS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
LOCASE_CHARACTERS = [
    'a',
    'b',
    'c',
    'd',
    'e',
    'f',
    'g',
    'h',
    'i',
    'j',
    'k',
    'm',
    'n',
    'o',
    'p',
    'q',
    'r',
    's',
    't',
    'u',
    'v',
    'w',
    'x',
    'y',
    'z',
]
UPCASE_CHARACTERS = [
    'A',
    'B',
    'C',
    'D',
    'E',
    'F',
    'G',
    'H',
    'I',
    'J',
    'K',
    'M',
    'N',
    'O',
    'p',
    'Q',
    'R',
    'S',
    'T',
    'U',
    'V',
    'W',
    'X',
    'Y',
    'Z',
]
SYMBOLS = ['#']
# combines all the character arrays above to form one array
COMBINED_LIST = DIGITS + UPCASE_CHARACTERS + LOCASE_CHARACTERS + SYMBOLS


class Clients(SuperOrOnboardUserRequiredMixin, ListView):
    """
    List clients related to same super user.
    Search clients by username, firstname or lastname by "search" query parameter.
    Filter clients by type 'active' or 'inactive' by "q" query parameter.
    """

    model = Client
    paginate_by = 6
    context_object_name = 'users'
    template_name = 'users/clients.html'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_onboard_user:
            qs = qs.filter(creator=self.request.user.my_onboard_setups.user_created)
        else:
            qs = qs.filter(creator=self.request.user)

        if self.request.GET.get("search"):
            search = self.request.GET.get("search")
            return qs.filter(
                Q(client__username__icontains=search)
                | Q(client__first_name__icontains=search)
                | Q(client__last_name__icontains=search)
            )

        if self.request.GET.get("q"):
            type_of = self.request.GET.get("q")
            if type_of == 'active':
                value = True
            elif type_of == 'inactive':
                value = False
            else:
                return qs
            return qs.filter(is_active=value)

        return qs


class SuperAdminRootSetup(SuperOrOnboardUserRequiredMixin, CreateView):
    """
    View for SuperAdmin for creating root user.
    """

    model = RootUser
    form_class = RootCreationForm
    template_name = 'entity/add_root.html'

    def get_success_url(self):
        if not (
            self.object.is_vodafone_default_onboarding
            or self.object.is_banks_standard_model_onboaring
        ):
            return reverse('data:main_view')

        token, created = ExpiringToken.objects.get_or_create(user=self.object)
        if created:
            return reverse('disbursement:add_agents', kwargs={'token': token.key})
        if token.expired():
            token.delete()
            token = ExpiringToken.objects.create(user=self.object)
        return reverse('disbursement:add_agents', kwargs={'token': token.key})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def handle_entity_extra_setups(self):
        entity_dict = {
            "user": self.request.user
            if self.request.user.is_superadmin
            else self.request.user.my_onboard_setups.user_created,
            "entity": self.object,
        }
        client_dict = {
            "creator": self.request.user
            if self.request.user.is_superadmin
            else self.request.user.my_onboard_setups.user_created,
            "client": self.object,
        }

        if (
            not self.object.is_vodafone_default_onboarding
            and not self.object.is_banks_standard_model_onboaring
        ):
            entity_dict['agents_setup'] = True
            entity_dict['fees_setup'] = True
            Budget.objects.create(disburser=self.object, created_by=self.request.user)

        if self.object.is_instant_model_onboarding:
            Setup.objects.create(
                user=self.object,
                pin_setup=True,
                levels_setup=True,
                maker_setup=True,
                checker_setup=True,
                category_setup=True,
            )
            CallWalletsModerator.objects.create(
                user_created=self.object,
                disbursement=False,
                change_profile=False,
                set_pin=False,
                user_inquiry=False,
                balance_inquiry=False,
            )
        elif (
            self.object.is_accept_vodafone_onboarding
            or self.object.is_vodafone_facilitator_onboarding
        ):
            if self.object.is_accept_vodafone_onboarding:
                entity_dict['is_normal_flow'] = False
            else:
                client_dict[
                    'vodafone_facilitator_identifier'
                ] = self.object.vodafone_facilitator_identifier
                entity_dict['is_normal_flow'] = True
            Setup.objects.create(user=self.object)
            CallWalletsModerator.objects.create(
                user_created=self.object,
                instant_disbursement=False,
                set_pin=False,
                user_inquiry=False,
                balance_inquiry=False,
            )
        else:
            client_dict['smsc_sender_name'] = self.object.smsc_sender_name
            client_dict[
                'agents_onboarding_choice'
            ] = self.object.agents_onboarding_choice
            Setup.objects.create(user=self.object)
            if self.object.is_banks_standard_model_onboaring:
                CallWalletsModerator.objects.create(
                    user_created=self.object,
                    instant_disbursement=False,
                    change_profile=False,
                )
            else:
                CallWalletsModerator.objects.create(
                    user_created=self.object, instant_disbursement=False
                )

        self.object.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )

        if self.request.user.is_onboard_user:
            client_dict['onboarded_by'] = self.request.user

        EntitySetup.objects.create(**entity_dict)
        Client.objects.create(**client_dict)

    def form_valid(self, form):
        self.object = form.save()
        self.handle_entity_extra_setups()
        msg = f"New Root/Admin created with username: {self.object.username}"
        logging_message(
            ROOT_CREATE_LOGGER, "[message] [NEW ADMIN CREATED]", self.request, msg
        )
        return HttpResponseRedirect(self.get_success_url())


class SuperAdminCancelsRootSetupView(SuperOwnsClientRequiredMixin, View):
    """
    View for canceling Root setups by deleting created entity setups.
    """

    def post(self, request, *args, **kwargs):
        """Handles POST requests to this View"""
        username = self.kwargs.get('username')

        try:
            User.objects.get(username=username).hard_delete()
            DELETE_USER_VIEW_LOGGER.debug(
                f"[message] [USER DELETED] [{request.user}] -- Deleted user: {username}"
            )
        except User.DoesNotExist:
            DELETE_USER_VIEW_LOGGER.debug(
                f"[message] [USER DOES NOT EXIST] [{request.user}] -- "
                f"tried to delete does not exist user with username {username}"
            )
        if self.request.user.is_onboard_user:
            return redirect(reverse("users:clients"))
        return redirect(reverse("data:e_wallets_home"))


class ClientFeesSetup(
    SuperOrOnboardUserRequiredMixin, SuperFinishedSetupMixin, CreateView
):
    """
    View for SuperAdmin to setup fees for the client
    """

    model = Client
    form_class = ClientFeesForm
    template_name = 'entity/add_client_fees.html'
    success_url = reverse_lazy('users:clients')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        root = ExpiringToken.objects.get(key=self.kwargs['token']).user
        kwargs.update({'instance': root.client})
        return kwargs


class ClientFeesUpdate(OnboardUserRequiredMixin, UpdateView):
    model = Client
    form_class = ClientFeesForm
    template_name = 'onboard/update_fees_profile.html'
    success_url = reverse_lazy('users:clients')

    def get_object(self, queryset=None):
        creator = self.request.user.my_onboard_setups.user_created
        return get_object_or_404(
            Client, creator=creator, client__username=self.kwargs.get('username')
        )


class CustomClientFeesProfilesUpdateView(
    SuperOwnsCustomizedBudgetClientRequiredMixin, UpdateView
):
    """
    View for updating client's fees profile
    """

    model = Client
    form_class = CustomClientProfilesForm
    template_name = 'entity/update_fees.html'

    def get_object(self, queryset=None):
        return get_object_or_404(
            Client,
            creator=self.request.user,
            client__username=self.kwargs.get('username'),
        )


class SuperAdminFeesProfileTemplateView(
    SuperWithAcceptVFAndVFFacilitatorOnboardingPermissionRequired, TemplateView
):
    """
    Template view for viewing the fees profile of a certain super admin with accept-vf onboarding setups
    """

    template_name = "users/fees_profile.html"


@login_required
def toggle_client(request):
    """
    Toggles Active status of specific client
    """

    if request.is_ajax() and request.method == 'POST' and request.user.is_superadmin:
        data = request.POST.copy()
        is_toggled = Client.objects.toggle(id=int(data['user_id']))
        return HttpResponse(
            content=json.dumps({"valid": is_toggled}), content_type="application/json"
        )

    raise Http404()


class OnboardingNewMerchant(DjangoAdminRequiredMixin, View):

    template_name = 'users/creation_admin.html'

    def get(self, request, *args, **kwargs):
        """Handles GET requests for credentials list view"""

        user_name = request.GET.get('user_name', None)
        Email = request.GET.get('admin_email', None)
        idms_user_id = request.GET.get('idms_user_id', None)
        mobile_number = request.GET.get('mobile_number', None)
        mid = request.GET.get('mid', None)
        intiail_dict = {
            'email': Email,
            'idms_user_id': idms_user_id,
            'username': user_name,
            'mobile_number': mobile_number,
            'mid': mid,
        }
        creation_form = CreationNewMerchantForm(initial=intiail_dict)
        context = {'form': creation_form}
        token = self.kwargs['token']
        access_token = AccessToken.objects.filter(token=self.token, used=False)
        if not access_token.exists():
            messages.error(request, "invalid link")
            return redirect(reverse('admin:index'))
        return render(request, template_name=self.template_name, context=context)

    def post(self, request, *args, **kwargs):
        """Handles POST requests to this View"""

        self.token = self.kwargs['token']
        access_token = AccessToken.objects.filter(token=self.token, used=False)
        if access_token:
            access_token = access_token[0]
            access_token.used = True
            access_token.save()
            form = CreationNewMerchantForm(request.POST)
            if form.is_valid():
                user_name = form.cleaned_data["username"]
                admin_email = form.cleaned_data["email"]
                idms_user_id = form.cleaned_data["idms_user_id"]
                mobile_number = form.cleaned_data["mobile_number"]
                mid = form.cleaned_data["mid"]
                onboard_business_model = form.cleaned_data["onboard_business_model"]
                if onboard_business_model == "portal":
                    root, exists = self.onboard_new_portal_user(
                        user_name, admin_email, idms_user_id, mobile_number, mid
                    )
                else:
                    root = self.onboard_new_integration_user(
                        user_name, admin_email, idms_user_id, mobile_number, mid
                    )
            messages.success(request, "Merchant onboarded successfully")
            return redirect(reverse('admin:index'))
        else:
            messages.error(request, "invalid link")
            return redirect(reverse('admin:index'))

    def define_new_admin_hierarchy(self, new_user):
        """
        Generate/Define the hierarchy of the new admin user
        :param new_user: the new admin user to be created
        :return: the new admin user with its new hierarchy
        """
        maximum = max(
            RootUser.objects.values_list('hierarchy', flat=True), default=False
        )
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

    def onboard_new_portal_user(
        self, user_name, root_email, idms_user_id, mobile_number, mid
    ):
        exists = False
        root = User.objects.filter(username=user_name)

        if root.exists():
            exists = True
            return root, exists

        else:
            try:
                if root_email == "":
                    root_email = f"{user_name}_portal_admin@paymob.com"
                # create root
                root = RootUser.objects.create(
                    username=user_name,
                    email=root_email,
                    user_type=3,
                    has_password_set_on_idms=True,
                    mobile_no=mobile_number,
                    mid=mid,
                    idms_user_id=idms_user_id,
                )
                # set admin hierarchy
                root = self.define_new_admin_hierarchy(root)
                # add root field when create root
                root.root = root
                root.idms_user_id = idms_user_id

                # add permissions
                root.user_permissions.add(
                    Permission.objects.get(
                        content_type__app_label='users',
                        codename='accept_vodafone_onboarding',
                    ),
                    Permission.objects.get(
                        content_type__app_label='users', codename='has_disbursement'
                    ),
                )
                root.save()

                superadmin = User.objects.get(
                    username=get_from_env("ACCEPT_VODAFONE_INTERNAL_SUPERADMIN")
                )

                entity_dict = {
                    "user": superadmin,
                    "entity": root,
                    "agents_setup": True,
                    "fees_setup": True,
                    "is_normal_flow": False,
                }
                client_dict = {
                    "creator": superadmin,
                    "client": root,
                }

                Setup.objects.create(
                    user=root
                )
                CallWalletsModerator.objects.create(
                    user_created=root,
                    instant_disbursement=False,
                    set_pin=False,
                    user_inquiry=False,
                    balance_inquiry=False,
                )

                EntitySetup.objects.create(**entity_dict)
                Client.objects.create(**client_dict)

                msg = f"New Root/Admin created with username: {root.username} by {self.request.user}"
                logging_message(
                    ROOT_CREATE_LOGGER,
                    "[message] [NEW ADMIN CREATED FROM ACCEPT]",
                    self.request,
                    msg,
                )

                # handle budget and fees setup
                if superadmin.vmt.vmt_environment == "STAGING":
                    root_budget = Budget.objects.create(
                        disburser=root, created_by=superadmin, current_balance=20000
                    )
                    FeeSetup.objects.create(
                        budget_related=root_budget,
                        issuer='vf',
                        fee_type='p',
                        percentage_value=get_from_env("VF_PERCENTAGE_VALUE"),
                    )
                    FeeSetup.objects.create(
                        budget_related=root_budget,
                        issuer='es',
                        fee_type='p',
                        percentage_value=get_from_env("ES_PERCENTAGE_VALUE"),
                    )
                    FeeSetup.objects.create(
                        budget_related=root_budget,
                        issuer='og',
                        fee_type='p',
                        percentage_value=get_from_env("OG_PERCENTAGE_VALUE"),
                    )
                    FeeSetup.objects.create(
                        budget_related=root_budget,
                        issuer='bw',
                        fee_type='p',
                        percentage_value=get_from_env("BW_PERCENTAGE_VALUE"),
                    )
                    FeeSetup.objects.create(
                        budget_related=root_budget,
                        issuer='am',
                        fee_type='p',
                        percentage_value=get_from_env("AM_PERCENTAGE_VALUE"),
                    )
                    FeeSetup.objects.create(
                        budget_related=root_budget,
                        issuer='bc',
                        fee_type='m',
                        fixed_value=0.0,
                        percentage_value=get_from_env("Bc_PERCENTAGE_VALUE"),
                        min_value=get_from_env("BC_min_VALUE"),
                        max_value=get_from_env("BC_max_VALUE"),
                    )
                else:
                    root_budget = Budget.objects.create(
                        disburser=root, created_by=superadmin, current_balance=0
                    )
                return root, exists

            except Exception as err:
                logging_message(
                    ROOT_CREATE_LOGGER,
                    "[error] [error when onboarding new client]",
                    self.request,
                    f"error :-  Error: {err.args}",
                )
                error_msg = "Process stopped during an internal error, please can you try again."
                error = {"message": error_msg}

    def onboard_new_integration_user(
        self, user_name, root_email, idms_user_id, mobile_number, mid
    ):

        try:
            # create root
            root = RootUser.objects.create(
                username=user_name,
                email=f"{user_name}_user_user@{user_name}.com",
                user_type=3,
                has_password_set_on_idms=True,
                mobile_no=mobile_number,
                mid=mid,
                idms_user_id=idms_user_id,
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
                Permission.objects.get(
                    content_type__app_label='users', codename='instant_model_onboarding'
                ),
                Permission.objects.get(
                    content_type__app_label='users', codename='has_instant_disbursement'
                ),
            )
            superadmin = User.objects.get(
                username=get_from_env("INTEGTATION_PATCH_SUPERADMIN")
            )

            # start create extra setup
            entity_dict = {
                "user": superadmin,
                "entity": root,
                "agents_setup": True,
                "fees_setup": True,
            }
            client_dict = {
                "creator": superadmin,
                "client": root,
            }

            Setup.objects.create(
                user=root,
                pin_setup=True,
                levels_setup=True,
                maker_setup=True,
                checker_setup=True,
                category_setup=True,
            )
            CallWalletsModerator.objects.create(
                user_created=root,
                disbursement=False,
                change_profile=False,
                set_pin=False,
                user_inquiry=False,
                balance_inquiry=False,
            )
            root.user_permissions.add(
                Permission.objects.get(
                    content_type__app_label='users', codename='has_disbursement'
                )
            )

            EntitySetup.objects.create(**entity_dict)
            Client.objects.create(**client_dict)
            # finish create extra setup

            msg = f"New Root/Admin created with username: {root.username} by {self.request.user.username}"
            logging_message(
                ROOT_CREATE_LOGGER, "[message] [NEW ADMIN CREATED]", self.request, msg
            )

            # handle budget and fees setup

            if superadmin.vmt.vmt_environment == "STAGING":
                root_budget = Budget.objects.create(
                    disburser=root, created_by=superadmin, current_balance=20000
                )
                FeeSetup.objects.create(
                    budget_related=root_budget,
                    issuer='vf',
                    fee_type='p',
                    percentage_value=get_from_env("VF_PERCENTAGE_VALUE"),
                )
                FeeSetup.objects.create(
                    budget_related=root_budget,
                    issuer='es',
                    fee_type='p',
                    percentage_value=get_from_env("ES_PERCENTAGE_VALUE"),
                )
                FeeSetup.objects.create(
                    budget_related=root_budget,
                    issuer='og',
                    fee_type='p',
                    percentage_value=get_from_env("OG_PERCENTAGE_VALUE"),
                )
                FeeSetup.objects.create(
                    budget_related=root_budget,
                    issuer='bw',
                    fee_type='p',
                    percentage_value=get_from_env("BW_PERCENTAGE_VALUE"),
                )
                FeeSetup.objects.create(
                    budget_related=root_budget,
                    issuer='am',
                    fee_type='p',
                    percentage_value=get_from_env("AM_PERCENTAGE_VALUE"),
                )
                FeeSetup.objects.create(
                    budget_related=root_budget,
                    issuer='bc',
                    fee_type='m',
                    fixed_value=0.0,
                    percentage_value=get_from_env("Bc_PERCENTAGE_VALUE"),
                    min_value=get_from_env("BC_min_VALUE"),
                    max_value=get_from_env("BC_max_VALUE"),
                )
            else:
                root_budget = Budget.objects.create(
                    disburser=root, created_by=superadmin, current_balance=0
                )

            # create dashboard user
            dashboard_user = InstantAPIViewerUser.objects.create(
                username=f"{user_name}_dashboard_user",
                email=root_email,
                user_type=7,
                root=root,
                hierarchy=root.hierarchy,
            )
            # generate strong password for dashboard user
            dashboard_user_pass = self.generate_strong_password(25)
            dashboard_user.set_password(dashboard_user_pass)
            dashboard_user.save()

            # create api checker
            api_checker = InstantAPICheckerUser.objects.create(
                username=f"{user_name}_api_checker",
                email=f"{user_name}_api_checker@{user_name}.com",
                user_type=6,
                root=root,
                hierarchy=root.hierarchy,
            )

            # generate strong password for api checker
            api_checker_pass = self.generate_strong_password(25)
            api_checker.set_password(api_checker_pass)
            api_checker.save()

            # create oauth2 provider app
            oauth2_app = Application.objects.create(
                client_type=Application.CLIENT_CONFIDENTIAL,
                authorization_grant_type=Application.GRANT_PASSWORD,
                name=f"{api_checker.username} OAuth App",
                user=api_checker,
            )

            # add permissions
            onboarding_permission = Permission.objects.get(
                content_type__app_label='users', codename='instant_model_onboarding'
            )
            api_docs_permission = Permission.objects.get(
                content_type__app_label='users', codename='can_view_api_docs'
            )

            dashboard_user.user_permissions.add(onboarding_permission)

            api_checker.user_permissions.add(onboarding_permission, api_docs_permission)
            dashboard_user_username = dashboard_user.username
            dashboard_user_password = dashboard_user_pass
            api_checker_username = api_checker.username
            api_checker_password = api_checker_pass
            oauth2_app_client_id = oauth2_app.client_id
            oauth2_app_client_secret = oauth2_app.client_secret

            if superadmin.vmt.vmt_environment == "STAGING":
                message = _(
                    f"""Dear Team,<br><br>
                    <label>Kindly find your credentials for initiating the testing phase of the integration</lable><br/>
                    <label>at the staging server https://stagingpayouts.paymobsolutions.com</lable><br/>
                    <label>Dashboard User:       </label> <br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Username:       </label> {dashboard_user_username}<br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Password:       </label> {dashboard_user_password}<br/>
                    <label>API User:       </label> <br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Username:       </label> {api_checker_username}<br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Password:       </label> {api_checker_password}<br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Client ID:       </label> {oauth2_app_client_id}<br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Client Secret:       </label> {oauth2_app_client_secret}<br/>
                    <label>Notes::       </label><br/><br/>
                    <label>&nbsp;&nbsp;.You have full access to the detailed API documentation at the home page's sidebar of the Dashboard user.  </label><br/>
                    <label>&nbsp;&nbsp;.Dashboard user have the ability to view the cashin transactions and search for specific one.</label><br/>
                    <label>&nbsp;&nbsp;.The API user won't have the ability to login to the portal, he/she is able to:</label><br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Generate, refresh tokens.        </label><br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Make instant disbursement requests.       </label><br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Inquire about transaction/(s) status.       </label><br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Inquire about his own current balance.       </label><br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Your current balance limit is 20000EG.       </label><br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; You can start testing at any time from now.       </label><br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Feel free to ask about any further details.       </label><br/>
                    <label>Best Regards</label>,
                    """
                )
            else:
                message = _(
                    f"""Dear Team,<br><br>
                    <label>Dashboard User:       </label> <br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Username:       </label> {dashboard_user_username}<br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Password:       </label> {dashboard_user_password}<br/>
                    <label>API User:       </label> <br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Username:       </label> {api_checker_username}<br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Password:       </label> {api_checker_password}<br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Client ID:       </label> {oauth2_app_client_id}<br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Client Secret:       </label> {oauth2_app_client_secret}<br/>
                    <label>Notes::       </label><br/><br/>
                    <label>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Your current balance limit is 20000EG.       </label><br/>
                    <label>Best Regards</label>,
                    """
                )

            from_email = settings.SERVER_EMAIL
            subject = "{}{}".format(root.username, _(" -Paymob Send Credentials"))
            recipient_list = [dashboard_user.email]

            mail_to_be_sent = EmailMultiAlternatives(
                subject, message, from_email, recipient_list
            )
            mail_to_be_sent.attach_alternative(message, "text/html")
            mail_to_be_sent.send()
            SEND_EMAIL_LOGGER.debug(f"[{subject}] [{recipient_list[0]}] -- {message}")

        except Exception as err:
            logging_message(
                ROOT_CREATE_LOGGER,
                "[error] [error when onboarding new client]",
                self.request,
                f"error :-  Error: {err.args}",
            )
            error_msg = (
                "Process stopped during an internal error, please can you try again."
            )
            error = {"message": error_msg}
