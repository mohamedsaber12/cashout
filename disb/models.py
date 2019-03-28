# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import models
from django.utils.translation import gettext_lazy as _


class VMTData(models.Model):
    """
    VMT is the credentials needed by UIG to request disbursement
    """
    # disbursment at checker user
    DISBURSEMENT = 1
    # balance inquiry at root user
    BALANCE_INQUIRY = 2
    # bulk msisdns change profile at root user
    CHANGE_PROFILE = 3
    # bulk agents set pin at root user
    SET_PIN = 4
    # bulk agents validation at superadmin
    USER_INQUIRY = 5

    login_username = models.CharField(max_length=32)
    login_password = models.CharField(max_length=32)
    request_gateway_code = models.CharField(max_length=32)
    request_gateway_type = models.CharField(max_length=32)
    wallet_issuer = models.CharField(max_length=64)
    vmt = models.OneToOneField(
        'users.SuperAdminUser',
        related_name='vmt',
        on_delete=models.CASCADE
    )
    vmt_environment = models.CharField(
        choices=[
            ('STAGING', 'STAGING'),
            ('PRODUCTION', 'PRODUCTION'),
            ('DEVELOPMENT', 'DEVELOPMENT'),
        ], max_length=16)

    def __str__(self):
        return "VMT for {} entities".format(self.vmt.username)

    def return_vmt_data(self,purpose):
        """
        Return dict of vmt data represented by VMT attributes used
        by the UIG
        :return:
        """
        data = {
            "LOGIN": self.login_password,
            "PASSWORD": self.login_password,
            "REQUEST_GATEWAY_CODE": self.request_gateway_code,
            "REQUEST_GATEWAY_TYPE": self.request_gateway_type,
            "WALLETISSUER": self.wallet_issuer,
        }
        if purpose == self.DISBURSEMENT:
            data.update({
                "SERVICETYPE": "P2P",
                "SOURCE": "DISB",
                "TYPE": "BPREQ",
            })
        elif purpose == self.USER_INQUIRY:
            data.update({
                "USERS": "",  # msisdn_list
                "TYPE": "BUSRINQREQ"
            })
        elif purpose == self.CHANGE_PROFILE:
            data.update({
                "USERS": "",  # msisdn
                "TYPE": "BCHGPREQ",
                "NEWPROFILE":""
            })
        elif purpose == self.SET_PIN:
            data.update({
                "USERS": "",  # msisdn_list
                "TYPE": "BPINSETREQ",
                "PIN": "" # pin
            })
        elif purpose == self.BALANCE_INQUIRY:
            data.update({
                "MSISDN": "",
                "PIN":"",
                "TYPE": "PRBALINQREQ"
            })
        return data




class Agent(models.Model):
    # root user
    wallet_provider = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='agents',on_delete=models.CASCADE)
    msisdn = models.CharField(max_length=14,verbose_name=_("Mobile number"))
    pin = models.BooleanField(default=False)
    super = models.BooleanField(default=False)

    def __str__(self):
        return self.msisdn


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
