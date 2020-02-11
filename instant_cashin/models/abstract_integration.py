# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AbstractVMTData(models.Model):
    """
    VMT is the credentials needed by UIG to make disbursement request
    """

    DISBURSEMENT = 1            # To make cash in
    BALANCE_INQUIRY = 2         # Inquire for Admin's Agents balance
    CHANGE_PROFILE = 3          # For List/Bulk of MSISDNs
    SET_PIN = 4                 # For List/Bulk of Agents
    USER_INQUIRY = 5            # For List/Bulk of Agents/MSISDNs validation as valid wallets
    INSTANT_DISBURSEMENT = 6    # For List/Bulk of Agents/MSISDNs validation as valid wallets

    login_username = models.CharField(_("UIG Login Username"), max_length=32)
    login_password = models.CharField(_("UIG Login Password"), max_length=32)
    request_gateway_code = models.CharField(_("UIG Request Gateway Code"), max_length=32)
    request_gateway_type = models.CharField(_("UIG Request Gateway Type"), max_length=32)
    wallet_issuer = models.CharField(_("UIG Wallet Issuer"), max_length=64)
    vmt_environment = models.CharField(
            _("VMT Environment"),
            choices=[
                ("PRODUCTION", "PRODUCTION"),
                ("STAGING", "STAGING"),
                ("DEVELOPMENT", "DEVELOPMENT"),
            ],
            max_length=16
    )
    vmt = models.OneToOneField(
            settings.AUTH_USER_MODEL,
            related_name="vmt",
            on_delete=models.CASCADE,
            verbose_name=_("VMT Credentials Owner")
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.vmt_environment} VMT credentials for {self.vmt.username}"

    def return_vmt_data(self, purpose):
        """
        :param SENDERS list of DISBURSEMENT request
        'SENDERS': [
            {'MSISDN': u'01001515153', 'PIN': u'112233'},
            {'MSISDN': u'01001515152', 'PIN': u'112233'},
            {'MSISDN': u'01173909090', 'PIN': u'112233'}
        ]
        :param RECIPIENTS list of DISBURSEMENT request
        'RECIPIENTS': [
            {'MSISDN': u'00201008005090', 'AMOUNT': 100.0, 'TXNID': 1},
            {'MSISDN': u'00201111710800', 'AMOUNT': 200.0, 'TXNID': 2}
        ]

        :return: Return dict of vmt data represented by VMT attributes used
        by the UIG
        """
        data = {
            "LOGIN": self.login_username,
            "PASSWORD": self.login_password,
            "REQUEST_GATEWAY_CODE": self.request_gateway_code,
            "REQUEST_GATEWAY_TYPE": self.request_gateway_type,
            "WALLETISSUER": self.wallet_issuer,
        }
        if purpose == self.DISBURSEMENT:
            data.update({
                "SENDERS": "",      # List of dictionaries of Agents with their pins
                "RECIPIENTS": "",   # List of MSISDNs to receive the amount of money being disbursed
                "PIN": "",          # Raw pin
                "SERVICETYPE": "P2P",
                "SOURCE": "DISB",
                "TYPE": "PPREQ"
            })
        elif purpose == self.INSTANT_DISBURSEMENT:
            data.update({
                "MSISDN": "",       # Agent - MUST be one of the agents list
                "MSISDN2": "",      # Consumer
                "AMOUNT": "",
                "PIN": "",          # Raw pin
                "IS_REVERSED": False,
                "TYPE": "PORCIREQ"
            })
        elif purpose == self.USER_INQUIRY:
            data.update({
                "USERS": "",        # MSISDNs List
                "TYPE": "BUSRINQREQ"
            })
        elif purpose == self.CHANGE_PROFILE:
            data.update({
                "USERS": "",        # MSISDNs List
                "NEWPROFILE": "",   # "Full", "Half" or "No fees"
                "TYPE": "BCHGPREQ",
            })
        elif purpose == self.SET_PIN:
            data.update({
                "USERS": "",        # MSISDNs List
                "PIN": "",          # Raw pin
                "TYPE": "BPINSETREQ",
            })
        elif purpose == self.BALANCE_INQUIRY:
            data.update({
                "MSISDN": "",       # Super agent ONLY, Not a list
                "PIN": "",          # Raw pin
                "TYPE": "PRBALINQREQ"
            })

        return data
