# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django import forms
from django.contrib.auth.models import Permission
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, FormView, TemplateView

from data.forms import FileCategoryFormSet
from data.models import FileCategory
from disbursement.forms import PinForm
from disbursement.models import Agent
from payouts.utils import get_dot_env
from users.decorators import root_only
from users.models import Client

from ..forms import (CheckerCreationForm, CheckerMemberFormSet, LevelFormSet,
                     MakerCreationForm, MakerMemberFormSet,
                     Vodafone_ChangePinForm)
from ..mixins import DisbursementRootRequiredMixin
from ..models import CheckerUser, Levels, MakerUser, Setup

WALLET_API_LOGGER = logging.getLogger("wallet_api")

MSG_TRY_OR_CONTACT = "can you try again or contact you support team"
MSG_PIN_SETTING_ERROR = _(
    f"Set pin process stopped during an internal error, {MSG_TRY_OR_CONTACT}"
)
import requests


class BaseFormsetView(TemplateView):
    """
    BaseView for setup Formsets
    """

    manual_setup = None

    def get_context_data(self, **kwargs):
        """update context data"""
        data = super().get_context_data(**kwargs)
        form = kwargs.get('form', None)
        data['form'] = form or self.form_class(
            queryset=self.get_queryset(),
            prefix=self.prefix,
            form_kwargs={'request': self.request},
        )
        data['enabled_steps'] = '-'.join(
            getattr(self.get_setup(), f'{self.data_type}_enabled_steps')()
        )
        return data

    def post(self, request, *args, **kwargs):
        form = self.form_class(
            request.POST, prefix=self.prefix, form_kwargs={'request': self.request}
        )
        if form.is_valid():
            return self.form_valid(form)

        return self.render_to_response(self.get_context_data(form=form))

    def get_setup(self):
        if self.manual_setup is None:
            self.manual_setup = Setup.objects.get(
                user__hierarchy=self.request.user.hierarchy
            )
        return self.manual_setup

    def form_valid(self, form):
        form.save()
        manual_setup = self.get_setup()
        setattr(manual_setup, f'{self.setup_key}_setup', True)
        manual_setup.save()
        return redirect(self.get_success_url())


class BaseAddMemberView(DisbursementRootRequiredMixin, CreateView):
    """
    Base View for creating maker and checker
    """

    template_name = 'users/add_member.html'

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.hierarchy = self.request.user.hierarchy
        self.object.save()
        self.object.user_permissions.add(
            *Permission.objects.filter(user=self.request.user)
        )
        return super().form_valid(form)


class PinFormView(DisbursementRootRequiredMixin, FormView):
    """
    Pin form view for the on-boarding phase of an entity/root
    """

    template_name = 'users/setting-up-disbursement/pin.html'
    manual_setup = None

    def get(self, request, *args, **kwargs):
        """Handle GET requests: instantiate a blank version of the form."""
        if request.GET.get('q', None) == 'next':
            manual_setup = self.get_setup()
            if manual_setup.pin_setup:
                return HttpResponseRedirect(self.get_success_url())
        return self.render_to_response(self.get_context_data())

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        return PinForm(root=self.request.user).get_form()

    def get_context_data(self, **kwargs):
        """update context data"""
        data = super().get_context_data(**kwargs)
        data['form_exist'] = bool(PinForm(root=self.request.user).get_form())
        data['enabled_steps'] = '-'.join(self.get_setup().disbursement_enabled_steps())
        return data

    def post(self, request, *args, **kwargs):
        form = PinForm(request.POST, root=request.user).get_form()
        if form and form.is_valid():
            ok = form.set_pin()
            if not ok:
                return self.form_invalid(form)
            manual_setup = self.get_setup()
            manual_setup.pin_setup = True
            manual_setup.save()
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_setup(self):
        if self.manual_setup is None:
            self.manual_setup = Setup.objects.get(
                user__hierarchy=self.request.user.hierarchy
            )
        return self.manual_setup

    def get_success_url(self):
        to_step = self.request.GET.get('to_step', None)
        if to_step == '3':
            return reverse('users:setting-disbursement-levels')
        if to_step == '4':
            return reverse('users:setting-disbursement-checkers')
        if to_step == '5':
            return reverse('users:setting-disbursement-formats')
        if self.request.user.from_accept and not self.request.user.allowed_to_be_bulk:
            return reverse('disbursement:single_step_list_create')
        return reverse('users:setting-disbursement-makers')


class MakerFormView(DisbursementRootRequiredMixin, BaseFormsetView):
    """
    Maker FormView for handling the on-boarding phase of makers for a new entity
    """

    template_name = 'users/setting-up-disbursement/makers.html'
    form_class = MakerMemberFormSet
    model = MakerUser
    prefix = 'maker'
    setup_key = 'maker'
    data_type = 'disbursement'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        manual_setup = self.get_setup()
        if not manual_setup.pin_setup:
            return reverse('users:setting-disbursement-pin')
        return self.render_to_response(self.get_context_data())

    def get_success_url(self):
        to_step = self.request.GET.get('to_step', None)
        if to_step == '1':
            return reverse('users:setting-disbursement-pin')
        if to_step == '4':
            return reverse('users:setting-disbursement-checkers')
        if to_step == '5':
            return reverse('users:setting-disbursement-formats')

        return reverse('users:setting-disbursement-levels')

    def get_queryset(self):
        return self.model.objects.filter(hierarchy=self.request.user.hierarchy)


class CheckerFormView(DisbursementRootRequiredMixin, BaseFormsetView):
    """
    Checker FormView for handling the on-boarding phase of checkers for a new entity
    """

    template_name = 'users/setting-up-disbursement/checkers.html'
    form_class = CheckerMemberFormSet
    model = CheckerUser
    prefix = 'checker'
    setup_key = 'checker'
    data_type = 'disbursement'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        manual_setup = self.get_setup()
        if not manual_setup.levels_setup:
            return reverse('users:setting-disbursement-levels')
        return self.render_to_response(self.get_context_data())

    def get_success_url(self):
        to_step = self.request.GET.get('to_step', None)
        if to_step == '1':
            return reverse('users:setting-disbursement-pin')
        if to_step == '2':
            return reverse('users:setting-disbursement-makers')
        if to_step == '3':
            return reverse('users:setting-disbursement-levels')

        return reverse('users:setting-disbursement-formats')

    def get_queryset(self):
        return self.model.objects.filter(hierarchy=self.request.user.hierarchy)


class LevelsFormView(DisbursementRootRequiredMixin, BaseFormsetView):
    """
    Levels of disbursement FormView for handling the on-boarding phase of checkers for a new entity
    """

    template_name = 'users/setting-up-disbursement/levels.html'
    form_class = LevelFormSet
    model = Levels
    prefix = 'level'
    data_type = 'disbursement'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""

        manual_setup = self.get_setup()
        if not manual_setup.maker_setup:
            return reverse('users:setting-disbursement-makers')
        return self.render_to_response(self.get_context_data())

    def get_success_url(self):
        to_step = self.request.GET.get('to_step', None)
        if to_step == '1':
            return reverse('users:setting-disbursement-pin')
        if to_step == '2':
            return reverse('users:setting-disbursement-makers')
        if to_step == '5':
            return reverse('users:setting-disbursement-formats')

        return reverse('users:setting-disbursement-checkers')

    def get_queryset(self):
        return self.model.objects.filter(created__hierarchy=self.request.user.hierarchy)

    def form_valid(self, form):
        form.save()
        Levels.update_levels_authority(self.request.user.root)
        manual_setup = self.get_setup()
        manual_setup.levels_setup = True
        manual_setup.save()
        return redirect(self.get_success_url())


class CategoryFormView(DisbursementRootRequiredMixin, BaseFormsetView):
    """
    Category FormView is for the on-boarding phase of the to-be-uploaded sheet specs for a new entity
    """

    template_name = 'users/setting-up-disbursement/category.html'
    form_class = FileCategoryFormSet
    model = FileCategory
    prefix = 'category'
    setup_key = 'category'
    data_type = 'disbursement'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        manual_setup = self.get_setup()
        if not manual_setup.checker_setup:
            return reverse('users:setting-disbursement-checkers')
        return self.render_to_response(self.get_context_data())

    def get_success_url(self):
        to_step = self.request.GET.get('to_step', None)
        if to_step == '1':
            return reverse('users:setting-disbursement-pin')
        if to_step == '2':
            return reverse('users:setting-disbursement-makers')
        if to_step == '3':
            return reverse('users:setting-disbursement-levels')
        if to_step == '4':
            return reverse('users:setting-disbursement-checkers')

        return reverse('data:e_wallets_home')

    def get_queryset(self):
        return self.model.objects.filter(
            user_created__hierarchy=self.request.user.hierarchy
        )


class AddMakerView(BaseAddMemberView):
    """
    View for creating maker
    """

    model = MakerUser
    form_class = MakerCreationForm

    def get_form_kwargs(self):
        """
        pass request to form kwargs
        """
        kwargs = super().get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {'who': _('maker'), 'success_url': reverse_lazy("users:add_maker")}
        )
        return context


class AddCheckerView(BaseAddMemberView):
    """
    View for creating checker
    """

    model = CheckerUser
    form_class = CheckerCreationForm

    def get_form_kwargs(self):
        """
        pass request to form kwargs
        """
        kwargs = super().get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {'who': _('checker'), 'success_url': reverse_lazy("users:add_checker")}
        )
        return context


class LevelsView(LevelsFormView):
    """View for adding levels"""

    template_name = 'users/add_levels.html'

    def get(self, request, *args, **kwargs):
        """Handle GET requests"""
        return self.render_to_response(self.get_context_data())

    def get_success_url(self):
        return reverse('users:levels')

    def get_context_data(self, **kwargs):
        """update context data"""
        data = super().get_context_data(**kwargs)
        form = kwargs.get('form', None)
        data['levelform'] = form or self.form_class(
            queryset=self.get_queryset(),
            prefix=self.prefix,
            form_kwargs={'request': self.request},
        )
        return data

    def form_valid(self, form):
        form.save()
        Levels.update_levels_authority(self.request.user.root)
        return redirect(self.get_success_url())


class ChangePinForm(forms.Form):
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(ChangePinForm, self).__init__(*args, **kwargs)

    new_pin = forms.CharField(min_length=6, max_length=6)
    password = forms.CharField(widget=forms.PasswordInput(), max_length=254)

    def clean(self):
        cleaned_data = super(ChangePinForm, self).clean()
        password = cleaned_data.get('password')
        new_pin = cleaned_data.get('new_pin')
        if not self.user.check_password(password):
            raise forms.ValidationError('Invalid password')
        if not new_pin.isdigit():
            raise forms.ValidationError('pin must be numeric only')


@root_only
def change_pin_view(
    request, template_name='users/change_pin.html', form_class=ChangePinForm
):
    if request.method == 'POST':
        form = form_class(request.user, request.POST)
        if form.is_valid():
            request.user.set_pin(form.cleaned_data['new_pin'])
            return render(
                request,
                template_name,
                {'message': 'Pin changed Successfully', 'form': form},
            )
    else:
        form = form_class(request.user)
    return render(request, template_name, {'form': form})


class vodafone_change_pin_view(View):
    template_name = 'users/vodafone_change_pin.html'
    form_class = Vodafone_ChangePinForm

    def get_transactions_error(self, transactions):
        failed_trx = list(filter(lambda trx: trx['TXNSTATUS'] != "200", transactions))

        if failed_trx:
            error_message = MSG_PIN_SETTING_ERROR
            for agent_index in range(len(failed_trx)):
                if failed_trx[agent_index]['TXNSTATUS'] == "407":
                    error_message = failed_trx[agent_index]['MESSAGE']
                    break

                elif failed_trx[agent_index]['TXNSTATUS'] == "608":
                    error_message = "Pin has been already registered for those agents. For assistance call 7001"
                    break

                elif failed_trx[agent_index]['TXNSTATUS'] == "1661":
                    error_message = (
                        "You cannot use an old PIN. For assistance call 7001"
                    )
                    break

            return error_message

        return None

    def call_wallet(self, root, pin, msisdns):
        superadmin = root.client.creator
        payload, payload_without_pin = superadmin.vmt.accumulate_set_pin_payload(
            msisdns, pin
        )
        env = get_dot_env()
        try:
            WALLET_API_LOGGER.debug(
                f"[request] [set pin] [{root}] -- {payload_without_pin}"
            )
            response = requests.post(
                env.str(superadmin.vmt.vmt_environment), json=payload, verify=False
            )
        except Exception as e:
            WALLET_API_LOGGER.debug(f"[message] [set pin error] [{root}] -- {e.args}")
            return None, MSG_PIN_SETTING_ERROR
        else:
            WALLET_API_LOGGER.debug(
                f"[response] [set pin] [{root}] -- {str(response.text)}"
            )

        if response.ok:
            response_dict = response.json()
            transactions = response_dict.get('TRANSACTIONS', None)
            if not transactions:
                error_message = response_dict.get('MESSAGE', None) or _(
                    "Failed to set pin"
                )
                return None, error_message
            return transactions, None
        return None, MSG_PIN_SETTING_ERROR

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.user, request.POST)
        if form.is_valid():
            raw_pin = form.cleaned_data['new_pin']
            root = request.user.root
            if request.user.root.is_vodafone_default_onboarding:
                agents = Agent.objects.filter(wallet_provider=root)
            else:
                agents = Agent.objects.filter(wallet_provider=root.super_admin)

            if request.user.root.client.agents_onboarding_choice in [
                Client.NEW_SUPERAGENT_AGENTS,
                Client.P2M,
            ]:
                msisdns = list(agents.values_list('msisdn', flat=True))
            elif (
                request.user.root.client.agents_onboarding_choice
                == Client.EXISTING_SUPERAGENT_NEW_AGENTS
            ):
                msisdns = list(
                    agents.filter(super=False).values_list('msisdn', flat=True)
                )
            else:
                msisdns = False

            if msisdns:
                transactions, error = self.call_wallet(root, raw_pin, msisdns)
                error = self.get_transactions_error(transactions)
                if error:  # handle transactions list
                    return render(
                        request, self.template_name, {'message': error, 'form': form}
                    )

            request.user.set_pin(form.cleaned_data['new_pin'])
            agents.update(pin=True)
            return render(
                request,
                self.template_name,
                {'message': 'Pin changed Successfully', 'form': form},
            )

        else:
            return render(request, self.template_name, {'form': form})

    def get(self, request, *args, **kwargs):
        form = self.form_class(request.user)
        return render(request, self.template_name, {'form': form})
