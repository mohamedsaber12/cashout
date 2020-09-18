# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


class AmanTransaction(models.Model):
    """
    Model for transactions disbursed through Aman channel
    """

    transaction_id = models.CharField(max_length=100, db_index=True, null=True)
    transaction_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    transaction = GenericForeignKey('transaction_type', 'transaction_id')
    is_paid = models.BooleanField(
            default=False,
            verbose_name=_("Is Paid?"),
            help_text=_("Updated at every notify_merchant_callback if the transaction is successfully paid")
    )
    bill_reference = models.PositiveIntegerField(
            db_index=True,
            default=0,
            verbose_name=_("Bill Reference")
    )

    class Meta:
        verbose_name = "Aman Transaction"
        verbose_name_plural = "Aman Transactions"
        get_latest_by = "-id"

    def __str__(self):
        """:return String representation of each client object"""
        return f"{self.transaction}"
