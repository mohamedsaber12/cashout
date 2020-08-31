# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.generic import UpdateView

from users.mixins import SuperOwnsCustomizedBudgetClientRequiredMixin

from .forms import BudgetModelForm
from .mixins import BudgetActionMixin
from .models import Budget


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
