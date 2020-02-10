# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

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
