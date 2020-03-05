from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import InstantTransaction


class InstantTransactionAdmin(admin.ModelAdmin):
    """
    Instant Transaction Admin model for the Instant Transaction model
    """

    default_fields = ['uid', 'from_user', 'anon_sender', 'anon_recipient', 'status']
    list_display = default_fields + ['created_at']
    readonly_fields = default_fields + ['uid', 'created_at']
    search_fields = list_display
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('from_user', )}),
        (_('Transaction Details'), {
            'fields': ('uid', 'status', 'anon_sender', 'anon_recipient', 'created_at', 'failure_reason')
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(InstantTransaction, InstantTransactionAdmin)
