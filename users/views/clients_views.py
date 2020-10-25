# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView, TemplateView
from rest_framework_expiring_authtoken.models import ExpiringToken

from utilities.logging import logging_message
from utilities.models import Budget, CallWalletsModerator

from ..forms import ClientFeesForm, CustomClientProfilesForm, RootCreationForm
from ..mixins import (
    SuperFinishedSetupMixin, SuperOwnsClientRequiredMixin,
    SuperOwnsCustomizedBudgetClientRequiredMixin,
    SuperRequiredMixin, UserWithAcceptVFOnboardingPermissionRequired,
)
from ..models import Client, EntitySetup, RootUser, User, Setup

ROOT_CREATE_LOGGER = logging.getLogger("root_create")
DELETE_USER_VIEW_LOGGER = logging.getLogger("delete_user_view")


class Clients(SuperRequiredMixin, ListView):
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
        qs = qs.filter(creator=self.request.user)

        if self.request.GET.get("search"):
            search = self.request.GET.get("search")
            return qs.filter(Q(client__username__icontains=search) |
                             Q(client__first_name__icontains=search) |
                             Q(client__last_name__icontains=search))

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


class SuperAdminRootSetup(SuperRequiredMixin, CreateView):
    """
    View for SuperAdmin for creating root user.
    """

    model = RootUser
    form_class = RootCreationForm
    template_name = 'entity/add_root.html'

    def get_success_url(self):

        if not self.object.is_vodafone_default_onboarding:
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
            "user": self.request.user,
            "entity": self.object
        }

        if not self.object.is_vodafone_default_onboarding:
            entity_dict["agents_setup"] = True
            entity_dict["fees_setup"] = True
            Budget.objects.create(disburser=self.object, created_by=self.request.user)

        if self.object.is_instant_model_onboarding:
            Setup.objects.create(
                    user=self.object, pin_setup=True, levels_setup=True, maker_setup=True, checker_setup=True,
                    category_setup=True
            )
            CallWalletsModerator.objects.create(
                    user_created=self.object, disbursement=False, change_profile=False, set_pin=False,
                    user_inquiry=False, balance_inquiry=False
            )
        elif self.object.is_accept_vodafone_onboarding:
            Setup.objects.create(user=self.object)
            CallWalletsModerator.objects.create(
                    user_created=self.object, instant_disbursement=False, set_pin=False,
                    user_inquiry=False, balance_inquiry=False
            )
        else:
            Setup.objects.create(user=self.object)
            CallWalletsModerator.objects.create(user_created=self.object, instant_disbursement=False)

        self.object.user_permissions.\
            add(Permission.objects.get(content_type__app_label='users', codename='has_disbursement'))
        EntitySetup.objects.create(**entity_dict)
        Client.objects.create(creator=self.request.user, client=self.object)

    def form_valid(self, form):
        self.object = form.save()
        self.handle_entity_extra_setups()
        msg = f"New Root/Admin created with username: {self.object.username}"
        logging_message(ROOT_CREATE_LOGGER, "[message] [NEW ADMIN CREATED]", self.request, msg)
        return HttpResponseRedirect(self.get_success_url())


class SuperAdminCancelsRootSetupView(SuperOwnsClientRequiredMixin, View):
    """
    View for canceling Root setups by deleting created entity setups.
    """

    def post(self, request, *args, **kwargs):
        """Handles POST requests to this View"""
        username = self.kwargs.get('username')

        try:
            User.objects.get(username=username).delete()
            DELETE_USER_VIEW_LOGGER.debug(f"[message] [USER DELETED] [{request.user}] -- Deleted user: {username}")
        except User.DoesNotExist:
            DELETE_USER_VIEW_LOGGER.debug(
                    f"[message] [USER DOES NOT EXIST] [{request.user}] -- "
                    f"tried to delete does not exist user with username {username}")

        return redirect(reverse("data:e_wallets_home"))


class ClientFeesSetup(SuperRequiredMixin, SuperFinishedSetupMixin, CreateView):
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


class CustomClientFeesProfilesUpdateView(SuperOwnsCustomizedBudgetClientRequiredMixin, UpdateView):
    """
    View for updating client's fees profile
    """

    model = Client
    form_class = CustomClientProfilesForm
    template_name = 'entity/update_fees.html'

    def get_object(self, queryset=None):
        return get_object_or_404(Client, creator=self.request.user, client__username=self.kwargs.get('username'))


class SuperAdminFeesProfileTemplateView(UserWithAcceptVFOnboardingPermissionRequired, TemplateView):
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
        return HttpResponse(content=json.dumps({"valid": is_toggled}), content_type="application/json")

    raise Http404()
