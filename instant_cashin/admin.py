from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Budget, InstantTransaction


class InstantTransactionAdmin(admin.ModelAdmin):
    """
    Instant Transaction Admin model for the Instant Transaction model
    """

    default_fields = ['uid', 'from_user', 'anon_sender', 'anon_recipient', 'status']
    fields =  default_fields + ['amount', 'failure_reason']
    list_display = default_fields + ['created_at']
    search_fields = list_display
    readonly_fields = ['uid', 'created_at']
    ordering = ['-created_at']

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + self.fields
        return self.readonly_fields


class BudgetAdmin(admin.ModelAdmin):
    """
    Budget Admin model for the Budget model
    """

    list_display = ['disburser', 'created_by', 'total_disbursed_amount', 'disbursed_amount', 'max_amount', 'updated_at']
    readonly_fields = ['total_disbursed_amount', 'updated_at', 'created_at', 'created_by']
    ordering = ['-updated_at']

    fieldsets = (
        (_("Users Details"), {'fields': ('disburser', 'created_by')}),
        (_("Budget Amount Details"), {'fields': ('total_disbursed_amount', 'max_amount', 'disbursed_amount')}),
        (_("Important Dates"), {'fields': ('updated_at', 'created_at')})
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


admin.site.register(InstantTransaction, InstantTransactionAdmin)
admin.site.register(Budget, BudgetAdmin)
