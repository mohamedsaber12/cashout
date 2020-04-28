# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .mixins import AdminSiteOwnerOnlyPermissionMixin
from .models import Agent, Budget, DisbursementData, DisbursementDocData, VMTData
from .utils import custom_budget_logger, custom_titled_filter


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    """
    Admin model for the tweaking the representation of the Agent model at the admin panel
    """

    list_display = ['msisdn', 'wallet_provider', 'super', 'pin']
    list_filter = ['pin', 'super', 'wallet_provider']


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    """
    Budget Admin model for the Budget model
    """

    list_filter = ['updated_at', 'created_at', 'disburser', 'created_by']
    list_display = ['disburser', 'created_by', 'total_disbursed_amount', 'disbursed_amount', 'max_amount', 'updated_at']
    readonly_fields = ['total_disbursed_amount', 'updated_at', 'created_at', 'created_by', 'current_balance']
    search_fields = ['disburser', 'created_by']
    ordering = ['-updated_at', '-created_at']

    fieldsets = (
        (_('Users Details'), {'fields': ('disburser', 'created_by')}),
        (
            _('Budget Amount Details'),
            {'fields': ('total_disbursed_amount', 'max_amount', 'disbursed_amount', 'current_balance')}
         ),
        (_('Important Dates'), {'fields': ('updated_at', 'created_at')})
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if not request.user.is_superuser or not request.user.is_superadmin:
            return readonly_fields + self.list_display
        return readonly_fields

    def current_balance(self, instance):
        """Show the final balance after all success cash-ins to the admin panel"""
        return instance.current_balance

    def has_add_permission(self, request):
        if not request.user.is_superuser or not request.user.is_superadmin:
            raise PermissionError(_("Only super users allowed to add to this table."))
        return True

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser or not request.user.is_superadmin:
            raise PermissionError(_("Only super users allowed to create/update at this table."))
        obj.created_by = request.user
        obj.save()

        newly_added_amount = abs(obj.max_amount - form.initial.get('max_amount', 0))
        custom_budget_logger(
                obj.disburser, f"New added amount: {newly_added_amount} LE",
                obj.created_by, head="[CUSTOM BUDGET - ADMIN PANEL]"
        )


@admin.register(DisbursementData)
class DisbursementDataAdmin(AdminSiteOwnerOnlyPermissionMixin, admin.ModelAdmin):
    """
    Admin panel representation for DisbursementData model
    """

    list_display = ['_trx_id', 'msisdn', 'amount', 'doc', 'is_disbursed', 'reason']
    list_filter = [
        ('doc__file_category__user_created__client__creator', custom_titled_filter('Super Admin')),
        ('doc__file_category__user_created', custom_titled_filter('Entity Admin')),
        ('doc__owner', custom_titled_filter('Document Owner/Uploader')),
        ('is_disbursed', custom_titled_filter('Disbursement Status')),
        'updated_at', 'created_at'
    ]
    ordering = ['-updated_at', '-created_at']

    fieldsets = (
        (None, {'fields': list_display}),
        (_('Important Dates'), {'fields': ('created_at', 'updated_at')})
    )

    def _trx_id(self, obj):
        """Add transaction id field renamed to Trx ID"""
        return obj.id
    _trx_id.short_description = "Trx ID"


@admin.register(DisbursementDocData)
class DisbursementDocDataAdmin(AdminSiteOwnerOnlyPermissionMixin, admin.ModelAdmin):
    """
    Admin panel representation for DisbursementDocData model
    """

    list_display = ['doc', 'txn_id', 'txn_status']
    list_filter = [('doc__owner', custom_titled_filter('Document Owner/Uploader'))]


@admin.register(VMTData)
class VMTDataAdmin(admin.ModelAdmin):
    """
    Admin model for VMTData credentials
    """

    list_filter = ['vmt']

    def has_add_permission(self, request):
        """
        :return: Prevent non superuser from adding new instances of VMTData credentials
        """
        if request.user.is_superuser:
            return True
        try:
            if request.user.root.vmt:
                return False
        except VMTData.DoesNotExist:
            return super(VMTDataAdmin, self).has_add_permission(request)
