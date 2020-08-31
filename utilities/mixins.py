# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin, messages
from django.forms import ModelForm, BaseInlineFormSet

from .functions import custom_budget_logger


class CustomInlineFormset(BaseInlineFormSet):
    """
    Custom formset that support initial data
    """

    def initial_form_count(self):
        """
        set 0 to use initial_extra explicitly.
        """
        if self.initial_extra:
            return 0
        else:
            return BaseInlineFormSet.initial_form_count(self)

    def total_form_count(self):
        """
        here use the initial_extra len to determine needed forms
        """
        if self.initial_extra:
            count = len(self.initial_extra) if self.initial_extra else 0
            count += self.extra
            return count
        else:
            return BaseInlineFormSet.total_form_count(self)


class CustomModelForm(ModelForm):
    """
    Custom model form that support initial data when save
    """

    def has_changed(self):
        """
        Returns True if we have initial data.
        """
        has_changed = ModelForm.has_changed(self)
        return bool(self.initial or has_changed)


class CustomInlineAdmin(admin.TabularInline):
    """
    Custom inline admin that support initial data
    """
    form = CustomModelForm
    formset = CustomInlineFormset


class BudgetActionMixin:
    """
    For handling BudgetModelForm at the used Views
    """

    @property
    def success_message(self):
        """For Budget Views to determine success flash message upon successful budget object update"""
        return NotImplemented

    @property
    def failure_message(self):
        """For Budget Views to determine failure flash message upon budget object update failure"""
        return NotImplemented

    def get_form_kwargs(self):
        """Injects forms with keyword arguments"""
        kwargs = super().get_form_kwargs()
        kwargs["budget_object"] = self.get_object()
        kwargs["superadmin_user"] = self.request.user

        return kwargs

    def form_valid(self, form):
        """Injects specific logic to the BudgetModelForm after form is validated successfully"""
        messages.success(self.request, self.success_message)
        custom_budget_logger(
                form.cleaned_data['disburser'].username,
                f"Total new added budget: {form.cleaned_data['new_amount']} LE",
                form.cleaned_data['created_by'].username
        )

        return super().form_valid(form)

    def form_invalid(self, form):
        """Injects specific logic to the BudgetModelForm after form is not validated successfully"""
        messages.error(self.request, self.failure_message)

        return super().form_invalid(form)
