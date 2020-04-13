# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import AmanTransaction, InstantTransaction


@admin.register(AmanTransaction)
class AmanTransactionAdmin(admin.ModelAdmin):
    """
    Admin model for Aman Instant Transaction model
    """

    list_display = ['transaction', 'entity', 'bill_reference', 'is_paid']
    readonly_fields = list_display
    search_fields = list_display
    list_filter = ['is_paid', 'transaction__from_user']

    def entity(self, instance):
        """Show the user who made the original transaction"""
        return instance.transaction.from_user

    def has_add_permission(self, request):      # ToDo: Refactor add/delete/change to permission mixin
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(InstantTransaction)
class InstantTransactionAdmin(admin.ModelAdmin):
    """
    Instant Transaction Admin model for the Instant Transaction model
    """

    default_fields = ['uid', 'from_user', 'anon_sender', 'anon_recipient', 'status', 'amount', 'issuer_type']
    list_display = default_fields + ['created_at', 'updated_at']
    readonly_fields = default_fields + ['uid', 'created_at']
    search_fields = list_display
    ordering = ['-updated_at', '-created_at']
    list_filter = ['from_user', 'status', 'issuer_type', 'anon_sender']

    fieldsets = (
        (None, {'fields': ('from_user', )}),
        (_('Transaction Details'), {
            'fields': ('uid', 'status', 'amount', 'issuer_type', 'anon_sender', 'anon_recipient', 'failure_reason')
        }),
        (_('Important Dates'), {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
