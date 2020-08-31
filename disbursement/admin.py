# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.shortcuts import resolve_url
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .mixins import AdminSiteOwnerOnlyPermissionMixin
from .models import Agent, DisbursementData, DisbursementDocData, VMTData
from .utils import custom_titled_filter


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    """
    Admin model for the tweaking the representation of the Agent model at the admin panel
    """

    list_display = ['msisdn', 'wallet_provider', 'super', 'pin', 'type']
    list_filter = ['pin', 'super', 'wallet_provider', 'type']


@admin.register(DisbursementData)
class DisbursementDataAdmin(AdminSiteOwnerOnlyPermissionMixin, admin.ModelAdmin):
    """
    Admin panel representation for DisbursementData model
    """

    list_display = ['_trx_id', 'msisdn', 'amount', 'issuer', 'doc', 'is_disbursed', 'reason']
    list_filter = [
        ('is_disbursed', custom_titled_filter('Disbursement Status')), 'issuer', 'created_at', 'updated_at',
        ('doc__file_category__user_created__client__creator', custom_titled_filter('Super Admin')),
        ('doc__file_category__user_created', custom_titled_filter('Entity Admin')),
        ('doc__owner', custom_titled_filter('Document Owner/Uploader'))
    ]
    search_fields = ['doc__id', 'msisdn', 'reason']
    ordering = ['-updated_at', '-created_at']

    fieldsets = (
        (None, {'fields': list_display + ["_disbursement_document"]}),
        (_('Important Dates'), {'fields': ('created_at', 'updated_at')})
    )

    def _trx_id(self, obj):
        """Add transaction id field renamed to Trx ID"""
        return obj.id
    _trx_id.short_description = "Trx ID"

    def _disbursement_document(self, instance):
        """Link to the original disbursement document"""
        url = resolve_url(admin_urlname(DisbursementDocData._meta, 'change'), instance.doc.disbursement_txn.id)
        return format_html(f"<a href='{url}'>{instance.doc.id}</a>")

    _disbursement_document.short_description = "Go to the disbursement document"


@admin.register(DisbursementDocData)
class DisbursementDocDataAdmin(AdminSiteOwnerOnlyPermissionMixin, admin.ModelAdmin):
    """
    Admin panel representation for DisbursementDocData model
    """

    list_display = ['doc', 'doc_status', 'txn_id', 'txn_status', 'has_callback', 'updated_at']
    list_filter = ['doc_status', ('doc__owner', custom_titled_filter('Document Owner/Uploader'))]
    search_fields = ['doc__id', 'txn_id']
    fieldsets = (
        (None, {'fields': ('doc', 'txn_id', 'txn_status', 'doc_status', 'has_callback')}),
        (_('Important Dates'), {'fields': ('created_at', 'updated_at')})
    )


@admin.register(VMTData)
class VMTDataAdmin(admin.ModelAdmin):
    """
    Admin model for VMTData credentials
    """

    list_filter = ['vmt', 'vmt_environment']
    list_display = list_filter + [
        'wallet_issuer', 'login_username', 'login_password', 'request_gateway_code', 'request_gateway_type'
    ]

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
