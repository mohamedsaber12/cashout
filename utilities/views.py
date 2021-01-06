# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import datetime

import logging

from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.generic import UpdateView, View
from django.core.files.storage import default_storage

from users.mixins import (SuperOwnsCustomizedBudgetClientRequiredMixin,
                          RootRequiredMixin)
from data.utils import deliver_mail
from instant_cashin.utils import get_from_env

from .forms import BudgetModelForm, IncreaseBalanceRequestForm
from .mixins import BudgetActionMixin
from .models import Budget

BUDGET_LOGGER = logging.getLogger("custom_budgets")


class BudgetUpdateView(SuperOwnsCustomizedBudgetClientRequiredMixin,
                       BudgetActionMixin,
                       UpdateView):
    """
    View for enabling SuperAdmin users to update and maintain custom Root budgets
    """
    model = Budget
    form_class = BudgetModelForm
    template_name = 'utilities/budget.html'
    context_object_name = 'budget_object'
    success_message = _("Budget updated successfully!")
    failure_message = _("Adding new budget failure, check below errors and try again!")

    def get_object(self, queryset=None):
        """Retrieve the budget object of the accessed disburser"""
        return get_object_or_404(Budget, disburser__username=self.kwargs["username"])

class IncreaseBalanceRequestView(RootRequiredMixin, View):
    """
    Request view for increase balance on accept vodafone admins
    """
    template_name = 'utilities/increase_balance_request.html'

    def get(self, request, *args, **kwargs):
        """Handles GET requests for Increase Balance Request"""
        context = {
            'request_received': False,
            'form': IncreaseBalanceRequestForm(),
        }
        return render(request, template_name=self.template_name, context=context)

    def post(self, request, *args, **kwargs):
        """Handles POST requests increase balance request"""
        context = {
            'form': IncreaseBalanceRequestForm(request.POST, request.FILES),
        }

        if context['form'].is_valid():
            form = context['form']
            BUDGET_LOGGER.debug(
                f"[response] [INCREASE BALANCE REQUEST] [{request.user}] -- With Payload {form.cleaned_data}"
            )
            # prepare email message
            message = _(f"""Dear <strong>Manger</strong><br><br>
            This E-mail to Inform you that this Account {request.user} has made request for 
            increase his balance <br/><br/>
            <label>Date/Time:-  </label> {datetime.now()}<br/><br/>
            <label>Amount To Be Added:-  </label>{form.cleaned_data['amount']}<br/><br/>
            <label>Type:-  </label> {form.cleaned_data['type'].replace("_", " ")} <br/><br/>
            """)
            rest_of_message = None
            if form.cleaned_data['type'] == 'from_accept_balance':
                rest_of_message = _(f"""<label>Accept username:-  </label> {form.cleaned_data['username']} <br/><br/>
                Thanks, BR""")
            else:
                rest_of_message = _(f"""<h4>From :- </h4>
                <label> Bank Name :-  </label> {form.cleaned_data['from_bank']} <br/><br/>
                <label> Account Number :-  </label> {form.cleaned_data['from_account_number']} <br/><br/>
                <label> Account Name :-  </label> {form.cleaned_data['from_account_name']} <br/><br/>
                <label> Date :-  </label> {form.cleaned_data['from_date']} <br/><br/>
                <h4>To:- </h4>
                <label> Bank Name :-  </label> {form.cleaned_data['to_bank']} <br/><br/>
                <label> Account Number :-  </label> {form.cleaned_data['to_account_number']} <br/><br/>
                <label> Account Name *:-  </label> {form.cleaned_data['to_account_name']} <br/><br/>
                Thanks, BR""")
            message += rest_of_message
            # prepare recipients list
            business_team = [dict(email=s, brand={'mail_subject':'Payout'}) for s in get_from_env('BUSINESS_TEAM').split(',')]
            if form.cleaned_data['type'] == 'from_accept_balance':
                deliver_mail(None, _(f"Transfer Request {request.user.username}"), message, business_team)
            else:
                # save image to media and get it's url
                proof_image = request.FILES['to_attach_proof']
                file_name = default_storage.save(proof_image.name, proof_image)
                # get file url
                file = default_storage.open(file_name)
                deliver_mail(None, _(f"Transfer Request {request.user.username}"), message, business_team, file)

            context = {
                'request_received': True,
                'form': IncreaseBalanceRequestForm(),
            }
        return render(request, template_name=self.template_name, context=context)
