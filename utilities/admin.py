# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.utils.translation import gettext_lazy as _

from .forms import BudgetAdminModelForm
from .functions import custom_budget_logger
from .mixins import CustomInlineAdmin
from .models import Budget, CallWalletsModerator, FeeSetup


@admin.register(CallWalletsModerator)
class CallWalletsModeratorAdmin(admin.ModelAdmin):
    """
    Customize the list view of the call wallets moderator model
    """

    list_display = [
        "user_created", "disbursement", "instant_disbursement", "change_profile", "set_pin", "user_inquiry",
        "balance_inquiry"
    ]


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    """
    Add LogEntry built-in model to the admin panel and customize its view.
    """

    readonly_fields = ['action_flag', 'action_time', 'user', 'content_type', 'object_repr', 'change_message']
    exclude = ['object_id']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class FeeSetupAdmin(CustomInlineAdmin):
    """
    FeeSetup inline Admin model for handling fees for every entity budget
    """

    model = FeeSetup
    extra = 0


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    """
    Budget Admin model for the Budget model
    """

    form = BudgetAdminModelForm
    inlines = [FeeSetupAdmin]
    list_filter = ['updated_at', 'created_at', 'created_by']
    list_display = ['disburser', 'current_balance', 'total_disbursed_amount', 'updated_at']
    readonly_fields = ['total_disbursed_amount', 'updated_at', 'created_at', 'created_by', 'current_balance']
    search_fields = ['disburser', 'created_by']
    ordering = ['-updated_at', '-created_at']

    fieldsets = (
        (_('Users Details'), {'fields': ('disburser', 'created_by')}),
        (
            _('Budget Amount Details'),
            {'fields': ('total_disbursed_amount', 'current_balance', 'add_new_amount', 'updated_at', 'created_at')}
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if not request.user.is_superuser or not request.user.is_superadmin:
            return readonly_fields + self.list_display
        return readonly_fields

    def has_add_permission(self, request):
        if not request.user.is_superuser or not request.user.is_superadmin:
            raise PermissionError(_("Only super users allowed to add to this table."))
        return True

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser or not request.user.is_superadmin:
            raise PermissionError(_("Only super users allowed to create/update at this table."))
        obj.created_by = request.user
        obj.save()
        custom_budget_logger(
                obj.disburser, f"New added amount: {form.cleaned_data['add_new_amount']} LE",
                obj.created_by, head="[message] [update from django admin]"
        )
