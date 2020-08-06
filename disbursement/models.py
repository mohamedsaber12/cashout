# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.models import AbstractTimeStamp
from utilities.models import AbstractBaseDocStatus, AbstractBaseVMTData


class VMTData(AbstractBaseVMTData):
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

    VODAFONE = 'V'
    ETISALAT = 'E'
    ORANGE = 'O'
    AGENT_TYPE_CHOICES = [
        (VODAFONE, _('vodafone')),
        (ETISALAT, _('etisalat')),
        (ORANGE, _('orange'))
    ]

    msisdn = models.CharField(max_length=14, verbose_name=_("Mobile number"))
    pin = models.BooleanField(default=False)
    super = models.BooleanField(default=False)
    type = models.CharField(
            _("agent type"),
            max_length=1,
            choices=AGENT_TYPE_CHOICES,
            default=VODAFONE,
            db_index=True,
    )
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


class DisbursementDocData(AbstractBaseDocStatus):
    """
    This model is just logs to the status of the doc disbursement action
    """

    doc = models.OneToOneField('data.Doc', null=True, related_name='disbursement_txn', on_delete=models.CASCADE)
    txn_id = models.CharField(max_length=16, null=True, blank=True)
    txn_status = models.CharField(max_length=16, null=True, blank=True)
    has_callback = models.BooleanField(default=False, verbose_name=_('Has Callback?'))
    doc_status = models.CharField(
            _("Document disbursement status"),
            max_length=1,
            choices=AbstractBaseDocStatus.STATUS_CHOICES,
            default=AbstractBaseDocStatus.DEFAULT
    )
    status = None

    class Meta:
        verbose_name = "Disbursement Document"
        verbose_name_plural = "Disbursement Documents"

    def __str__(self):
        """String representation for disbursement doc data model objects"""
        return f"{self.txn_id} -- {self.doc.id}"

    def mark_doc_status_processed_successfully(self):
        """Mark disbursement doc status as processed successfully"""
        self.doc_status = DisbursementDocData.PROCESSED_SUCCESSFULLY
        self.save()

    def mark_doc_status_processing_failure(self):
        """Mark disbursement doc status as processing failure"""
        self.doc_status = DisbursementDocData.PROCESSING_FAILURE
        self.save()

    def mark_doc_status_disbursed_successfully(self, transaction_id, transaction_status):
        """
        Mark disbursement doc status as disbursed successfully
        :param transaction_id: transaction id from the disbursement response
        :param transaction_status: transaction status from the disbursement response
        """
        self.txn_id = transaction_id
        self.txn_status = transaction_status
        self.doc_status = DisbursementDocData.DISBURSED_SUCCESSFULLY
        self.save()

    def mark_doc_status_disbursement_failure(self):
        """Mark disbursement doc status as disbursement failure"""
        self.doc_status = DisbursementDocData.DISBURSEMENT_FAILURE
        self.save()


class DisbursementData(AbstractTimeStamp):
    """
    This model to save data processed from the document like FileData yet for disbursement
    """

    doc = models.ForeignKey('data.Doc', null=True, related_name='disbursement_data', on_delete=models.CASCADE)
    is_disbursed = models.BooleanField(default=0)
    amount = models.FloatField(verbose_name=_('AMOUNT'))
    msisdn = models.CharField(max_length=16, verbose_name=_('Mobile Number'))
    issuer = models.CharField(max_length=8, verbose_name=_('Issuer Option'), default='default', db_index=True)
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

    disburser = models.OneToOneField(
            "users.RootUser",
            on_delete=models.CASCADE,
            related_name="budget",
            verbose_name=_("Owner/Admin of the Disburser"),
            help_text=_("Before every cashin transaction, the amount to be disbursed "
                        "will be validated against the current balance of the (API)-Checker owner")
    )
    created_by = models.ForeignKey(
            "users.SuperAdminUser",
            on_delete=models.CASCADE,
            related_name='budget_creator',
            verbose_name=_("Maintainer - Super Admin"),
            null=True,
            help_text=_("Super Admin who created/updated this budget values")
    )
    current_balance = models.DecimalField(
            _("Current Balance"),
            max_digits=10,
            decimal_places=2,
            default=0,
            null=True,
            blank=True,
            help_text=_("Updated automatically after any disbursement callback or any addition from add_new_amount")
    )
    total_disbursed_amount = models.DecimalField(
            _("Total Disbursed Amount"),
            max_digits=15,
            decimal_places=2,
            default=0,
            null=False,
            blank=False,
            help_text=_("Updated automatically after any disbursement callback")
    )
    vodafone_percentage = models.DecimalField(
            _("Vodafone Trx Percentage"),
            validators=[
                MinValueValidator(round(Decimal(0.1), 1)),
                MaxValueValidator(round(Decimal(100.0), 1))
            ],
            max_digits=5,
            decimal_places=1,
            default=0,
            null=False,
            blank=False,
            help_text=_("ONLY applied at Vodafone transactions")
    )
    etisalat_percentage = models.DecimalField(
            _("Etisalat Trx Percentage"),
            validators=[
                MinValueValidator(round(Decimal(0.1), 1)),
                MaxValueValidator(round(Decimal(100.0), 1))
            ],
            max_digits=5,
            decimal_places=1,
            default=0,
            null=False,
            blank=False,
            help_text=_("ONLY applied at Etisalat transactions")
    )
    orange_percentage = models.DecimalField(
            _("Orange Trx Percentage"),
            validators=[
                MinValueValidator(round(Decimal(0.1), 1)),
                MaxValueValidator(round(Decimal(100.0), 1))
            ],
            max_digits=5,
            decimal_places=1,
            default=0,
            null=False,
            blank=False,
            help_text=_("ONLY applied at Orange transactions")
    )
    aman_percentage = models.DecimalField(
            _("Aman Trx Percentage"),
            validators=[
                MinValueValidator(round(Decimal(0.1), 1)),
                MaxValueValidator(round(Decimal(100.0), 1))
            ],
            max_digits=5,
            decimal_places=1,
            default=0,
            null=False,
            blank=False,
            help_text=_("ONLY applied at Aman transactions")
    )
    ach_percentage = models.DecimalField(
            _("ACH Trx Percentage"),
            validators=[
                MinValueValidator(round(Decimal(0.1), 1)),
                MaxValueValidator(round(Decimal(100.0), 1))
            ],
            max_digits=5,
            decimal_places=1,
            default=0,
            null=False,
            blank=False,
            help_text=_("ONLY applied at ACH transactions")
    )

    class Meta:
        verbose_name = "Custom Budget"
        verbose_name_plural = "Custom Budgets"
        get_latest_by = "-updated_at"
        ordering = ["-created_at"]

    def __str__(self):
        """String representation for a custom budget object"""
        return f"{self.disburser.username} Custom Budget"

    def get_absolute_url(self):
        """Success form submit - object saving url"""
        return reverse("disbursement:budget_update", kwargs={"username": self.disburser.username})

    def accumulate_amount_with_fees_and_vat(self, amount_to_be_disbursed, issuer_type):
        """Accumulate amount being disbursed with fees percentage and 14 % VAT"""
        actual_amount = round(Decimal(amount_to_be_disbursed), 2)

        if issuer_type == "vodafone":
            percentage = round(self.vodafone_percentage, 2)
        elif issuer_type == "etisalat":
            percentage = round(self.etisalat_percentage, 2)
        elif issuer_type == "orange":
            percentage = round(self.orange_percentage, 2)
        elif issuer_type == "aman":
            percentage = round(self.aman_percentage, 2)
        else:
            percentage = round(self.ach_percentage, 2)

        fees_value = round(((actual_amount * percentage) / 100), 2)
        vat_value = round(((fees_value * Decimal(14.00)) / 100), 2)
        total_amount_with_fees_and_vat = round((actual_amount + fees_value + vat_value), 2)

        return total_amount_with_fees_and_vat

    def within_threshold(self, amount_to_be_disbursed, issuer_type):
        """
        Check if the amount to be disbursed won't exceed the current balance
        :param amount_to_be_disbursed: Amount to be disbursed at the currently running transaction
        :param issuer_type: Channel/Issuer used to disburse the amount over
        :return: True/False
        """
        try:
            amount_plus_fees_vat = self.accumulate_amount_with_fees_and_vat(amount_to_be_disbursed, issuer_type)

            if amount_plus_fees_vat <= round(self.current_balance, 2):
                return True
            return False
        except (ValueError, Exception) as e:
            raise ValueError(_(f"Error while checking the amount to be disbursed if within threshold - {e.args}"))

    def update_disbursed_amount_and_current_balance(self, amount, issuer_type):
        """
        Update the total disbursement amount and the current balance after each successful transaction
        :param amount: the amount being disbursed
        :param issuer_type: Channel/Issuer used to disburse the amount over
        :return: True/False
        """
        try:
            amount_plus_fees_vat = self.accumulate_amount_with_fees_and_vat(amount, issuer_type)
            self.total_disbursed_amount += amount_plus_fees_vat
            self.current_balance -= amount_plus_fees_vat
            self.save()
        except Exception:
            raise ValueError(
                    _(f"Error updating the total disbursed amount and the current balance, please retry again later.")
            )

        return True
