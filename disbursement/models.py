# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid

from phonenumber_field.modelfields import PhoneNumberField

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import AbstractTimeStamp, AbstractBaseStatus
from utilities.models import (
    AbstractBaseDocStatus, AbstractBaseVMTData, AbstractTransactionCategory,
    AbstractTransactionCurrency, AbstractTransactionPurpose,
)


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
            settings.AUTH_USER_MODEL,
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
    reference_id = models.CharField(
            _('Reference ID'),
            max_length=30,
            default='None',
            null=False
    )
    aman_obj = GenericRelation(
            "instant_cashin.AmanTransaction",
            object_id_field="transaction_id",
            content_type_field="transaction_type",
            related_query_name="aman_manual"
    )

    class Meta:
        verbose_name = "Disbursement Data Record"
        verbose_name_plural = "Disbursement Data Records"
        unique_together = ('doc', 'msisdn')
        index_together = ['doc', 'msisdn']
        get_latest_by = ['id']

    def __str__(self):
        return self.msisdn

    @property
    def get_is_disbursed(self):
        return 'Successful' if self.is_disbursed else 'Failed'

    @property
    def aman_transaction_is_paid(self):
        """Property for retrieving is_paid status for disbursement records through Aman"""
        try:
            return self.aman_obj.first().is_paid
        except AttributeError:
            return None


class BankTransaction(AbstractTimeStamp,
                      AbstractBaseStatus,
                      AbstractTransactionCategory,
                      AbstractTransactionCurrency,
                      AbstractTransactionPurpose):
    """
    Model for managing bank transactions.
    """

    # transaction_batch = models.ForeignKey(
    #         self,
    #         on_delete=models.CASCADE,
    #         related_name=_('')
    # )
    user_created = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name=_('bank_transactions'),
            verbose_name=_('Disburser')
    )
    id = models.UUIDField(
            _('Bank Transaction ID'),
            primary_key=True,
            default=uuid.uuid4,
            unique=True,
            editable=False,
            help_text=_("New one generated everytime send_trx request made to EBC")
    )
    message_id = models.UUIDField(
            _('Message ID'),
            db_index=True,
            default=uuid.uuid4,
            unique=True,
            editable=False,
            help_text=_("New one generated everytime send_trx or get_trx_status request made to EBC")
    )
    transaction_status_code = models.CharField(
            _('Transaction Status Code'),
            max_length=4,
            blank=True,
            null=True
    )
    transaction_status_description = models.CharField(
            _('Transaction Status Description'),
            max_length=255,
            blank=True,
            null=True
    )
    debtor_account = models.CharField(
            _('Corporate Account Number'),
            max_length=34,
            help_text=_('The company/service provider account number')
    )
    amount = models.DecimalField(
            _('Amount'),
            max_digits=12,
            decimal_places=2,
    )
    creditor_name = models.CharField(
            _('Beneficiary Name'),
            max_length=70,
            help_text=_('The customer/receiver name')
    )
    creditor_account_number = models.CharField(
            _('Beneficiary Account Number'),
            max_length=34,
            help_text=_('The customer/receiver bank account')
    )
    creditor_bank = models.CharField(
            _('Beneficiary Bank'),
            max_length=11,
            help_text=_('The bank where the customer/receiver maintains its accounts')
    )
    creditor_bank_branch = models.CharField(
            _('Beneficiary Bank Branch'),
            max_length=35,
            blank=True,
            default='',
    )
    end_to_end = models.CharField(
            _('Optional Transaction Identifier 1'),
            max_length=35,
            blank=True,
            default=''
    )
    instruction_id = models.CharField(
            _('Optional Transaction Identifier 2'),
            max_length=35,
            blank=True,
            default=''
    )
    creditor_email = models.EmailField(
            _('Beneficiary Email'),
            max_length=70,
            blank=True,
            null=True
    )
    creditor_mobile_number = PhoneNumberField(
            _('Beneficiary Mobile Number'),
            region='EG',
            blank=True,
            null=True
    )
    corporate_code = models.CharField(
            _('Corporate Code'),
            max_length=50,
            help_text=_('Corporate Code to identify corporate')
    )
    sender_id = models.CharField(
            _('Sender ID'),
            max_length=35,
            blank=True,
            default=''
    )
    creditor_id = models.CharField(
            _('Creditor ID'),
            max_length=35,
            blank=True,
            default=''
    )
    creditor_address_1 = models.CharField(
            _('Creditor Address 1'),
            max_length=70,
            blank=True,
            default=''
    )
    creditor_address_2 = models.CharField(
            _('Creditor Address 2'),
            max_length=70,
            blank=True,
            default=''
    )
    debtor_address_1 = models.CharField(
            _('Debtor Address 1'),
            max_length=70,
            blank=True,
            default=''
    )
    debtor_address_2 = models.CharField(
            _('Debtor Address 2'),
            max_length=70,
            blank=True,
            default=''
    )
    debtor_address_3 = models.CharField(
            _('Debtor Address 3'),
            max_length=70,
            blank=True,
            default=''
    )
    debtor_address_4 = models.CharField(
            _('Debtor Address 4'),
            max_length=70,
            blank=True,
            default=''
    )
    additional_info_1 = models.CharField(
            _('Remittance Info 1'),
            max_length=140,
            blank=True,
            default=''
    )
    additional_info_2 = models.CharField(
            _('Remittance Info 2'),
            max_length=140,
            blank=True,
            default=''
    )

    class Meta:
        verbose_name = 'Bank Transaction'
        verbose_name_plural = 'Bank Transactions'
        get_latest_by = '-created_at'
        ordering = ['-created_at', '-updated_at']

    def mark_successful(self):
        """Mark transaction status as successful"""
        self.status = self.SUCCESSFUL
        self.save()

    def mark_failed(self):
        """Mark transaction status as failed"""
        self.status = self.FAILED
        self.save()

    def mark_pending(self):
        """Mark transaction status as pending"""
        self.status = self.PENDING
        self.save()
