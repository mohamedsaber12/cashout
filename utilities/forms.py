# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal
from http import client

from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext as _

from utilities.models.generic_models import TopupAction

from .models import Budget
import logging
BUDGET_LOGGER = logging.getLogger("custom_budgets")




class BudgetModelForm(forms.ModelForm):
    """
    Budget form is for enabling SuperAdmin users to track and maintain Admin users budgets
    """
    new_amount = forms.IntegerField(
            label=_('Amount to be added'),
            required=False,
            validators=[MinValueValidator(round(Decimal(0), 2))],
            widget=forms.TextInput(attrs={'placeholder': _('New budget, ex: 100')})
    )
    readonly_fields = ['current_balance', 'disburser', 'created_by']

    class Meta:
        model = Budget
        fields = ['new_amount', 'current_balance', 'disburser', 'created_by']
        labels = {
            'created_by': _('Last update done by'),
        }

    def __init__(self, *args, **kwargs):
        """Set any extra fields expected to passed from any BudgetView uses the BudgetModelForm"""
        self.budget_object = kwargs.pop('budget_object', None)
        self.superadmin_user = kwargs.pop('superadmin_user', None)

        super().__init__(*args, **kwargs)

        # ToDo: Make all of the fields other than the new budget are readonly fields
        # This doesn't work because of modelform saving issues
        # for field in self.readonly_fields:
        #     self.fields[field].widget.attrs['disabled'] = 'true'
        #     self.fields[field].required = False

    def clean(self):
        """
        1. Validate and add the cleaned  value of the new_amount to the current balance
        2. Assign created_by value to the current SuperAdmin who owns this Root/Disburser
        """
        cleaned_data = super().clean()

        try:
            amount_being_added = cleaned_data.get('new_amount', None)
            if amount_being_added:
                amount_being_added = round(Decimal(amount_being_added), 2)
                cleaned_data["current_balance"] = self.budget_object.current_balance + amount_being_added
                cleaned_data["created_by"] = self.superadmin_user
        except ValueError:
            self.add_error('new_amount', _('New amount must be a valid integer, please check and try again.'))

        return cleaned_data


class BudgetAdminModelForm(forms.ModelForm):
    """
    Admin model form for adding new amounts to the current balance of a budget record
    """
    add_new_amount = forms.IntegerField(
            required=False,
            validators=[MinValueValidator(round(Decimal(0), 2))],
            widget=forms.TextInput(attrs={'placeholder': _('Add New budget, ex: 100')})
    )
    fx_rate = forms.FloatField(
        required=False,
        validators=[MinValueValidator(round(Decimal(0.1), 2)), MaxValueValidator((round(Decimal(100), 2)))],
        help_text=_('If the amount charged by USD please add the fx rate if not leave empty '),
        widget=forms.TextInput(attrs={'placeholder': _('FX rate ')}))

    def save(self, commit=True):
        """Update the current balance using the newly added amount"""
        try:
            amount_being_added = self.cleaned_data.get('add_new_amount', None)
            balance_before = self.instance.current_balance
            fx_amount = 0
            fx_rate = self.cleaned_data.get('fx_rate', None)
            if amount_being_added:
                amount_being_added = round(Decimal(amount_being_added), 2)
                if fx_rate:
                    fx_amount = amount_being_added * Decimal(fx_rate/100)
                    new_amount = round(amount_being_added - fx_amount, 2)
                    BUDGET_LOGGER.debug(
                        f"FX rate applied ({fx_rate}) amount before {amount_being_added} amount after {new_amount}"
                        )
                    amount_being_added = new_amount
                self.instance.current_balance += amount_being_added
                TopupAction.objects.create(
                    client=self.instance.disburser,
                    amount=Decimal(amount_being_added),
                    balance_before=Decimal(balance_before),
                    balance_after=Decimal(self.instance.current_balance),
                    fx_ratio_amount=Decimal(fx_amount),
                )



        except ValueError:
            self.add_error('add_new_amount', _('New amount must be a valid integer, please check and try again.'))

        return super().save(commit=commit)

    class Meta:
        model = Budget
        fields = ['add_new_amount']


class IncreaseBalanceRequestForm(forms.Form):
    """
    form For Increase Balance Request
    """
    amount = forms.IntegerField(
        label=_('Amount To Be Added '),
        required=True,
        validators=[MinValueValidator(round(Decimal(100), 2))],
        widget=forms.TextInput(attrs={
            'placeholder': _('New budget, ex: 100'),
            'class': 'form-control',
            'type': 'number'
        })
    )
    type = forms.ChoiceField(
        label=_('Type'),
        required=True,
        choices=[
            ('from_bank_transfer', _('Bank Transfer')),
            ('from_accept_balance', _('From Accept Balance')),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control',
        })
    )
    currency = forms.ChoiceField(
            label=_('Currency'),
            required=True,
            choices=[
                ('egyptian_pound', _('Egyptian Pound (L.E)')),
                ('american_dollar', _('American Dollar ($)'))
            ],
            widget=forms.Select(attrs={
                'class': 'form-control',
            })
    )
    username = forms.CharField(
        label=_('username'),
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': _('Accept Username'),
            'class': 'form-control'
        })
    )
    from_bank = forms.CharField(
        label=_('bank'),
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': _('Bank Name'),
            'class': 'form-control'
        })
    )
    to_bank = forms.CharField(
        label=_('bank'),
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': _('Bank Name'),
            'class': 'form-control'
        })
    )
    from_account_number = forms.CharField(
        label=_('acc. number'),
        required=False,
        max_length=34,
        widget=forms.TextInput(attrs={
            'placeholder': _('From Account Number'),
            'class': 'form-control'
        })
    )
    to_account_number = forms.CharField(
        label=_('acc. number'),
        required=False,
        max_length=34,
        widget=forms.TextInput(attrs={
            'placeholder': _('To Account Number'),
            'class': 'form-control'
        })
    )
    from_account_name = forms.CharField(
        label=_('account name'),
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': _('From Account Name'),
            'class': 'form-control'
        })
    )
    to_account_name = forms.CharField(
        label=_('account number'),
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': _('To Account Name'),
            'class': 'form-control'
        })
    )
    from_date = forms.DateField(
        label=_('date'),
        required=False,
        widget=forms.DateInput(attrs={
            'placeholder': _('Enter Date'),
            'class': 'form-control'
        })
    )
    to_attach_proof = forms.FileField(
        label=_('Attach Proof'),
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'custom-file-input'
        })
    )

    def clean(self):
        data = self.cleaned_data
        transfer_type = data.get('type')
        is_required_msg = 'This field is required'
        error_file_size_msg = 'The uploaded attachment size must be less than 3 MB'
        validationErrors = {}

        if transfer_type == 'from_accept_balance':
            if not data.get('username'):
                validationErrors['username'] = [is_required_msg]
        elif transfer_type == 'from_bank_transfer':
            if not data.get('from_bank'):
                validationErrors['from_bank'] = [is_required_msg]
            if not data.get('from_account_number'):
                validationErrors['from_account_number'] = [is_required_msg]
        # validate shared fields between bank deposit and bank transfer
        if transfer_type == 'from_bank_deposit' or transfer_type == 'from_bank_transfer':
            if not data.get('to_bank'):
                validationErrors['to_bank'] = [is_required_msg]
            if not data.get('to_account_number'):
                validationErrors['to_account_number'] = [is_required_msg]
            if not data.get('from_account_name'):
                validationErrors['from_account_name'] = [is_required_msg]
            if not data.get('to_account_name'):
                validationErrors['to_account_name'] = [is_required_msg]
            if not data.get('from_date'):
                validationErrors['from_date'] = [is_required_msg]
            if not data.get('to_attach_proof'):
                validationErrors['to_attach_proof'] = [is_required_msg]
            else:
                if not self.validate_image():
                    validationErrors['to_attach_proof'] = [error_file_size_msg]
        if len(validationErrors.keys()) == 0:
            return data
        raise forms.ValidationError(validationErrors)

    def validate_image(self):
        filesize = self.cleaned_data.get('to_attach_proof').size
        megabyte_limit = 2.8
        if filesize > megabyte_limit*1024*1024:
            return False
        return True
