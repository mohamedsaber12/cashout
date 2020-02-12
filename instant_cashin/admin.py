from django.contrib import admin

from .models.instant_transactions import InstantTransaction


class InstantTransactionAdmin(admin.ModelAdmin):

    list_display = ['uid', 'from_user', 'anon_sender', 'anon_recipient', 'status', 'created_at']
    search_fields = ['uid', 'from_user', 'anon_sender', 'anon_recipient', 'status', 'created_at']
    readonly_fields = ['uid', 'status', 'from_user', 'anon_sender', 'anon_recipient', 'amount', 'created_at', 'failure_reason']
    ordering = ['-created_at']


    # ToDo - Adding last_success transactions, last_fail_transactions
    # actions = ['last_success_transactions']
    # def last_success_transactions(self, request, queryset):
    #     queryset.filter(status="S")
    #
    # last_success_transactions.short_description = "Return the last succeeded transactions"

admin.site.register(InstantTransaction, InstantTransactionAdmin)
