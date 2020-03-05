# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Agent, Budget, VMTData


class VMTDataAdmin(admin.ModelAdmin):
    """
    Admin model for VMTData credentials
    """

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


class BudgetAdmin(admin.ModelAdmin):
    """
    Budget Admin model for the Budget model
    """

    list_display = ['disburser', 'created_by', 'total_disbursed_amount', 'disbursed_amount', 'max_amount', 'updated_at']
    readonly_fields = ['total_disbursed_amount', 'updated_at', 'created_at', 'created_by']
    search_fields = ['disburser', 'created_by']
    ordering = ['-updated_at']

    fieldsets = (
        (_('Users Details'), {'fields': ('disburser', 'created_by')}),
        (_('Budget Amount Details'), {'fields': ('total_disbursed_amount', 'max_amount', 'disbursed_amount')}),
        (_('Important Dates'), {'fields': ('updated_at', 'created_at')})
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


admin.site.register(Agent)
admin.site.register(Budget, BudgetAdmin)
admin.site.register(VMTData, VMTDataAdmin)
