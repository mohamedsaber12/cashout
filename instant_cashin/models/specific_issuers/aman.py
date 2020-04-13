# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import gettext_lazy as _

from ..instant_transactions import InstantTransaction


class AmanTransaction(models.Model):
    """
    Model for instant transactions make to Aman channel
    """

    transaction = models.ForeignKey(
            InstantTransaction,
            db_index=True,
            on_delete=models.CASCADE,
            related_name=_("aman_transaction"),
            verbose_name=_("Aman Transaction")
    )
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
        return f"{self.transaction.uid}"

    def update_bill_reference(self, bill_ref):
        """Updates the transaction bill reference after each successful aman specific transaction"""
        self.bill_reference = bill_ref
        self.save()
