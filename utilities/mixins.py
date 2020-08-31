# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.forms import ModelForm, BaseInlineFormSet


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
