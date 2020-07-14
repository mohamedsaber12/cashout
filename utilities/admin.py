# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.admin.models import LogEntry

from .models import CallWalletsModerator


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
