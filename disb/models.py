# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.models import AbstractTimeStamp
from instant_cashin.models import AbstractVMTData


class VMTData(AbstractVMTData):
    """
    VMT Data Credentials to make requests to UIG
    """

    vmt = models.OneToOneField(
            'users.SuperAdminUser',
            related_name="vmt",
            on_delete=models.CASCADE,
            verbose_name=_("VMT Credentials Owner")
    )

    class Meta:
        verbose_name = "VMT Credential"
        verbose_name_plural = "VMT Credentials"


class Agent(models.Model):
    """
    Model for representing every admin related super-agent and agents
    """
    msisdn = models.CharField(max_length=14, verbose_name=_("Mobile number"))
    pin = models.BooleanField(default=False)
    super = models.BooleanField(default=False)
    wallet_provider = models.ForeignKey(
            "users.RootUser",
            related_name="agents",
            on_delete=models.CASCADE,
            help_text=_("Each super-agent or agent MUST be related to specific Root user")
    )

    def __str__(self):
        """
        :return: String representation of each agent object
        """
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

    class Meta:
        verbose_name = "Disbursement Document"
        verbose_name_plural = "Disbursement Documents"


class DisbursementData(AbstractTimeStamp):
    """
    This model to save data processed from the document like FileData yet for disbursement
    """
    doc = models.ForeignKey('data.Doc', null=True, related_name='disbursement_data', on_delete=models.CASCADE)
    is_disbursed = models.BooleanField(default=0)
    amount = models.FloatField(verbose_name=_('AMOUNT'))
    msisdn = models.CharField(max_length=16, verbose_name=_('Mobile Number'))
    reason = models.TextField()

    class Meta:
        verbose_name = "Disbursement Data Record"
        verbose_name_plural = "Disbursement Data Records"
        unique_together = ('doc', 'msisdn')
        index_together = ['doc', 'msisdn']

    def __str__(self):
        return self.msisdn

    @property
    def get_is_disbursed(self):
        return 'Successful' if self.is_disbursed else 'Failed'


class Budget(AbstractTimeStamp):
    """
    Model for checking budget before executing disbursement
    """

    max_amount = models.DecimalField(
            _("Max Allowed Amount"),
            max_digits=10,
            decimal_places=2,
            default=0,
            null=False,
            blank=False
    )
    disbursed_amount = models.DecimalField(
            _("Disbursed Amount"),
            max_digits=10,
            decimal_places=2,
            default=0,
            null=False,
            blank=False
    )
    total_disbursed_amount = models.DecimalField(
            _("Total Previously Disbursed Amount"),
            max_digits=15,
            decimal_places=2,
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
                        "amount to be disbursed will be validated against this checker's/admin's budget limit")
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
        :return: decimal, current root/admin user's balance
        """
        return round((self.max_amount - self.disbursed_amount), 2)

    def get_absolute_url(self):
        """Success form submit - object saving url"""
        return reverse("disbursement:budget_update", kwargs={"username": self.disburser.username})

    def within_threshold(self, amount_to_be_disbursed):
        """
        Check if the amount to be disbursed plus the previously disbursed amount won't exceed the max_amount
        :param amount_to_be_disbursed: Amount to be disbursed at the currently running transaction
        :return: True/False
        """
        new_amount = round((self.disbursed_amount + Decimal(amount_to_be_disbursed)), 2)

        if not new_amount <= self.max_amount:
            return False
        return True

    def update_disbursed_amount(self, amount):
        """
        Update the total disbursement amount at each successful transaction
        :param amount: the amount to be disbursed
        :return: True/False
        """
        try:
            disbursed_amount = round(Decimal(amount), 2)
            self.total_disbursed_amount += disbursed_amount
            self.disbursed_amount += disbursed_amount
            self.save()
        except Exception as e:
            raise ValueError(_(f"Error updating the total disbursed amount, please retry again later."))

        return True
