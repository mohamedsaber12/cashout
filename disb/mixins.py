# -*- coding: UTF-8 -*-
from django.contrib import messages

from disb.utils import custom_budget_logger


class AdminSiteOwnerOnlyPermissionMixin:
    """
    For handling add/change/delete permission at the admin panel
    """

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser or request.user == obj.doc.owner.root.super_admin or \
                request.user == obj.doc.owner.root:
            return True
        raise PermissionError(_("Only admin family member users allowed to delete records from this table."))

    def has_change_permission(self, request, obj=None):
        return False


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
