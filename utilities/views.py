# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import datetime

import logging

from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.generic import UpdateView, View

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
            'form': IncreaseBalanceRequestForm(request.POST),
        }

        if context['form'].is_valid():
            form = context['form']
            BUDGET_LOGGER.debug(
                f"[response] [INCREASE BALANCE REQUEST] [{request.user}] -- With Payload {form.cleaned_data}"
            )
            message = _(f"""Dear <strong>Manger</strong><br><br>
            This E-mail to Inform you that this Account {request.user} has made request for 
            increase his balance <br/><br/>
            <label>Date/Time:-  </label> {datetime.now()}<br/><br/>
            <label>Amount To Be Added:-  </label>{form.cleaned_data['amount']}<br/><br/>
            <label>Type:-  </label> {form.cleaned_data['type'].replace("_", " ")} <br/><br/>
            Thanks, BR""")

            business_team = [dict(email=s, brand={'mail_subject':'Payout'}) for s in get_from_env('BUSINESS_TEAM').split(',')]
            deliver_mail(None, _(f"Increase Balance Request From {request.user}"), message, business_team)

            context = {
                'request_received': True,
                'form': IncreaseBalanceRequestForm(),
            }
        return render(request, template_name=self.template_name, context=context)
