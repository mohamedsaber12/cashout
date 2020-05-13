# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

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
