from django.contrib import admin

from .models.instant_transactions import InstantTransaction


class InstantTransactionAdmin(admin.ModelAdmin):

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


admin.site.register(InstantTransaction, InstantTransactionAdmin)
