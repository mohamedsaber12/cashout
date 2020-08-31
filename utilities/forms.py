# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal

from django import forms
from django.core.validators import MinValueValidator
from django.utils.translation import gettext as _

from .models import Budget


class BudgetAdminModelForm(forms.ModelForm):
    """
    Admin model form for adding new amounts to the current balance of a budget record
    """

    add_new_amount = forms.IntegerField(
            required=False,
            validators=[MinValueValidator(round(Decimal(100), 2))],
            widget=forms.TextInput(attrs={'placeholder': _('Add New budget, ex: 100')})
    )

    def save(self, commit=True):
        """Update the current balance using the newly added amount"""
        try:
            amount_being_added = self.cleaned_data.get('add_new_amount', None)
            if amount_being_added:
                amount_being_added = round(Decimal(amount_being_added), 2)
                self.instance.current_balance += amount_being_added

        except ValueError:
            self.add_error('add_new_amount', _('New amount must be a valid integer, please check and try again.'))

        return super().save(commit=commit)

    class Meta:
        model = Budget
        fields = ['add_new_amount']
