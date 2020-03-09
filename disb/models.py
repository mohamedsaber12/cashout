# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import AbstractTimeStamp
from instant_cashin.models import AbstractVMTData


class VMTData(AbstractVMTData):
    """VMT Data Credentials to make requests to UIG"""

    vmt = models.OneToOneField(
            'users.SuperAdminUser',
            related_name="vmt",
            on_delete=models.CASCADE,
            verbose_name=_("VMT Credentials Owner")
    )


class Agent(models.Model):
    # root user
    wallet_provider = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='agents',on_delete=models.CASCADE)
    msisdn = models.CharField(max_length=14,verbose_name=_("Mobile number"))
    pin = models.BooleanField(default=False)
    super = models.BooleanField(default=False)

    def __str__(self):
        if self.super:
            return f"SuperAgent {self.msisdn} for Root: {self.wallet_provider.username}"
        return f"Agent {self.msisdn} for Root: {self.wallet_provider.username}"


class DisbursementDocData(models.Model):
    """
    This model is just logs to the status of the doc disbursement action
    """
    doc = models.OneToOneField('data.Doc', null=True, related_name='disbursement_txn', on_delete=models.CASCADE)
    txn_id = models.CharField(max_length=16, null=True, blank=True)  #
    txn_status = models.CharField(max_length=16, null=True, blank=True)


class DisbursementData(models.Model):
    """
    This model to save data processed from the document like FileData yet for disbursement
    """
    doc = models.ForeignKey('data.Doc', null=True, related_name='disbursement_data', on_delete=models.CASCADE)
    date = models.DateField(blank=True, null=True)
    is_disbursed = models.BooleanField(default=0)
    amount = models.FloatField(verbose_name=_('AMOUNT'))
    msisdn = models.CharField(max_length=16, verbose_name=_('Mobile Number'))
    reason = models.TextField()

    class Meta:
        unique_together = ('doc', 'msisdn')
        index_together = ['doc', 'msisdn']

    def __str__(self):
        return self.msisdn

    @property
    def get_is_disbursed(self):
        return 'Yes' if self.is_disbursed else 'No'


class Budget(AbstractTimeStamp):
    """
    Model for checking budget before executing disbursement
    """

    max_amount = models.IntegerField(_("Max Allowed Amount"), default=0, null=False, blank=False)
    disbursed_amount = models.IntegerField(_("Disbursed Amount"), default=0, null=False, blank=False)
    total_disbursed_amount = models.IntegerField(
            _("Total Previously Disbursed Amount"),
            default=0,
            null=False,
            blank=False
    )
    disburser = models.OneToOneField(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name='budget',
            verbose_name=_("Disburser"),
            help_text=_("Before every cashin transaction, "
                        "amount to be disbursed will be validated against this checker's budget limit")
    )
    created_by = models.ForeignKey(
            "users.SuperAdminUser",
            on_delete=models.CASCADE,
            null=True,
            related_name='budget_creator',
            verbose_name=_("Maintainer Admin"),
            help_text=_("Admin who created/updated this budget values")
    )

    class Meta:
        verbose_name = "Allowed Budget"
        verbose_name_plural = "Allowed Budgets"
        get_latest_by = "-updated_at"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.disburser.username} Budget"

    @property
    def current_balance(self):
        """
        :return: int, current root/admin user's balance
        """
        return self.max_amount - self.disbursed_amount

    def within_threshold(self, amount_to_be_disbursed):
        """
        Check if the amount to be disbursed plus the previously disbursed amount won't exceed the max_amount
        :param amount_to_be_disbursed: Amount to be disbursed at the currently running transaction
        :return: True/False
        """
        new_amount = int(self.disbursed_amount) + int(amount_to_be_disbursed)

        if not int(new_amount) <= int(self.max_amount):
            return False
        return True

    def update_disbursed_amount(self, amount):
        """
        Update the total disbursement amount at each successful transaction
        :param amount: the amount to be disbursed
        :return: True/False
        """
        if not self.within_threshold(amount):
            return False

        self.total_disbursed_amount += int(amount)
        self.disbursed_amount += int(amount)
        self.save()
        return True
