# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class CallWalletsModerator(models.Model):
    """
    Moderator to manage calls/requests to the wallets
    """

    disbursement = models.BooleanField(default=True)
    instant_disbursement = models.BooleanField(default=True)
    change_profile = models.BooleanField(default=True)
    set_pin = models.BooleanField(default=True)
    user_inquiry = models.BooleanField(default=True)
    balance_inquiry = models.BooleanField(default=True)
    user_created = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name=_("callwallets_moderator"),
            verbose_name=_("The moderator admin")
    )

    class Meta:
        verbose_name = "Call Wallets Moderator"
        verbose_name_plural = "Call Wallets Moderators"
        ordering = ["-id"]

    def __str__(self):
        """String representation for the moderator model objects"""
        return f"{self.user_created.username} moderator"
