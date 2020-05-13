# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AbstractBaseVMTData(models.Model):
    """
    VMT is the credentials needed by UIG to make disbursement request
    """

    DISBURSEMENT = 1
    INSTANT_DISBURSEMENT = 2
    CHANGE_PROFILE = 3          # List/Bulk of consumers
    SET_PIN = 4                 # List/Bulk of agents
    USER_INQUIRY = 5            # List/Bulk of agents/consumers
    BALANCE_INQUIRY = 6

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
        """String representation for a VMT data object"""
        return f"{self.vmt.username} - {self.vmt_environment}"

    def return_vmt_data(self, purpose):
        """
        Example:
            {
                'LOGIN'               : 'FUND_CONSTANT',
                'PASSWORD'            : 'FUND_CONSTANT',
                'REQUEST_GATEWAY_CODE': 'FUND_CONSTANT',
                'REQUEST_GATEWAY_TYPE': 'FUND_CONSTANT',
                'WALLETISSUER'        : 'VODAFONE',
                'PIN'                 : '123456',
                'SERVICETYPE'         : 'P2P',
                'SOURCE'              : 'DISB',
                'TYPE'                : 'PPREQ',
                'SENDERS'             : [
                    {'MSISDN': '01001515153', 'PIN': '112233'},
                    {'MSISDN': '01001515152', 'PIN': '112233'},
                    {'MSISDN': '01173909090', 'PIN': '112233'}
                ],
                'RECIPIENTS'          : [
                    {'MSISDN': '00201008005090', 'AMOUNT': 100.0, 'TXNID': 1},
                    {'MSISDN': '00201111710800', 'AMOUNT': 200.0, 'TXNID': 2}
                ]
            }

        :return: Return dict of vmt data represented by VMT attributes used by the UIG
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
                "SENDERS": "",      # List of dicts of Agents with their pins
                "RECIPIENTS": "",   # List of consumers
                "PIN": "",          # Raw pin
                "SERVICETYPE": "P2P",
                "SOURCE": "DISB",
                "TYPE": "PPREQ"
            })
        elif purpose == self.INSTANT_DISBURSEMENT:
            data.update({
                "MSISDN": "",       # Agent
                "MSISDN2": "",      # Consumer
                "AMOUNT": "",
                "PIN": "",          # Raw pin
                "IS_REVERSED": False,
                "TYPE": "PORCIREQ"
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
        elif purpose == self.USER_INQUIRY:
            data.update({
                "USERS": "",        # MSISDNs List
                "TYPE": "BUSRINQREQ"
            })
        elif purpose == self.BALANCE_INQUIRY:
            data.update({
                "MSISDN": "",       # Super agent ONLY, one msisdn Not list
                "PIN": "",          # Raw pin
                "TYPE": "PRBALINQREQ"
            })

        return data
