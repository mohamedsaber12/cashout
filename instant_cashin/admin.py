# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter

from django.contrib import admin
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import resolve_url
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from disbursement.models import DisbursementData
from .models import AmanTransaction, InstantTransaction
from .mixins import ExportCsvMixin
from core.models import AbstractBaseStatus


class AmanTransactionTypeFilter(admin.SimpleListFilter):
    title = "Transaction Type"
    parameter_name = "transaction_type"

    def lookups(self, request, model_admin):
        return(
            ("manual_transaction", "Disbursement Data Record"),
            ("instant_transaction", "Instant Transaction")
        )

    def queryset(self, request, queryset):
        if self.value() == "manual_transaction":
            return queryset.filter(transaction_type=ContentType.objects.get_for_model(DisbursementData))
        if self.value() == 'instant_transaction':
            return queryset.filter(transaction_type=ContentType.objects.get_for_model(InstantTransaction))


class CustomStatusFilter(admin.SimpleListFilter):
    title = 'Status'
    parameter_name = 'status_choice_verbose'

    def lookups(self, request, model_admin):
        return AbstractBaseStatus.STATUS_CHOICES + [
            ('U', _("Unknown")),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(status=value)
        return queryset


@admin.register(AmanTransaction)
class AmanTransactionAdmin(admin.ModelAdmin):
    """
    Admin model for Aman Instant Transaction model
    """

    list_display = ['transaction_id', 'transaction_type', 'disburser', 'bill_reference', 'is_paid']
    readonly_fields = list_display + ['original_transaction_url']
    search_fields = ['transaction_id']
    list_filter = ['is_paid', AmanTransactionTypeFilter]

    def disburser(self, instance):
        """Show the user who made the original transaction"""
        if instance.transaction_type:
            if instance.transaction_type.name == "Disbursement Data Record":
                return instance.transaction.doc.disbursed_by
            else:
                return instance.transaction.from_user

    def original_transaction_url(self, instance):
        """Create link to the original transaction"""
        if instance.transaction_type:
            if instance.transaction_type.name == "Disbursement Data Record":
                url = resolve_url(admin_urlname(DisbursementData._meta, 'change'), instance.transaction.id)
                return format_html(f"<a href='{url}'>{instance.transaction.id}</a>")
            else:
                url = resolve_url(admin_urlname(InstantTransaction._meta, 'change'), instance.transaction.uid)
                return format_html(f"<a href='{url}'>{instance.transaction.uid}</a>")

    original_transaction_url.short_description = "Go To Transaction Details"

    def has_add_permission(self, request):      # ToDo: Refactor add/delete/change to permission mixin
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(InstantTransaction)
class InstantTransactionAdmin(admin.ModelAdmin, ExportCsvMixin):
    """
    Instant Transaction Admin model for the Instant Transaction model
    """

    default_fields = [
        'uid', 'from_user', 'anon_recipient', 'status_choice_verbose', 'transaction_status_code', 'amount', 'issuer_type'
    ]
    list_display = default_fields + ['updated_at', 'disbursed_date']
    readonly_fields = default_fields + ['uid', 'created_at']
    search_fields = ['uid', 'anon_recipient']
    ordering = ['-created_at']
    list_filter = [
        ('disbursed_date', DateRangeFilter),
        ('created_at', DateRangeFilter),
        CustomStatusFilter,
        'issuer_type', 'anon_sender', 'from_user', 'is_single_step', 'transaction_status_code'
    ]
    actions = ["export_as_csv"]
    fieldsets = (
        (None, {'fields': ('from_user', )}),
        (_('Transaction Details'), {
            'fields': (
                'uid', 'reference_id', 'status_choice_verbose', 'amount', 'issuer_type', 'anon_sender', 'anon_recipient',
                'recipient_name', 'transaction_status_code', 'transaction_status_description', 'document'
            )
        }),
        (_('Important Dates'), {
            'fields': ('created_at', 'updated_at', 'disbursed_date')
        }),
    )

    def has_module_permission(self, request):
        if request.user.is_superuser or request.user.is_finance_with_instant_transaction_view:
            return True

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser or request.user.is_finance_with_instant_transaction_view:
            return True

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

