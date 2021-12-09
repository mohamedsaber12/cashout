# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import copy

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import AbstractTimeStamp


class AbstractBaseDocStatus(AbstractTimeStamp):
    """
    Base Document Status model.
    """

    # choices
    DEFAULT = 'd'
    UPLOADED_SUCCESSFULLY = '1'
    PROCESSING_FAILURE = '2'
    PROCESSED_SUCCESSFULLY = '3'
    DISBURSEMENT_FAILURE = '4'
    DISBURSED_SUCCESSFULLY = '5'

    STATUS_CHOICES = [
        (DEFAULT, _("Default")),
        (UPLOADED_SUCCESSFULLY, _("Uploaded Successfully")),
        (PROCESSING_FAILURE, _("Processing Failure")),
        (PROCESSED_SUCCESSFULLY, _("Processed Successfully")),
        (DISBURSEMENT_FAILURE, _("Disbursement Failure")),
        (DISBURSED_SUCCESSFULLY, _("Disbursed Successfully")),
    ]

    status = models.CharField(
            _("status"), max_length=1, choices=STATUS_CHOICES, default=DEFAULT
    )

    class Meta:
        abstract = True


class AbstractBaseDocType(AbstractTimeStamp):
    """
    Base Document Type model.
    """

    # choices
    E_WALLETS = 1
    COLLECTION = 2
    BANK_WALLETS = 3
    BANK_CARDS = 4

    TYPES_CHOICES = [
        (E_WALLETS, _("E-wallets")),
        (COLLECTION, _("Collection")),
        (BANK_WALLETS, _("Bank wallets")),
        (BANK_CARDS, _("Bank cards"))
    ]

    type_of = models.PositiveSmallIntegerField(_("Type"), db_index=True, choices=TYPES_CHOICES, default=E_WALLETS)

    class Meta:
        abstract = True


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
    DISBURSEMENT_OR_CHANGE_PROFILE_CALLBACK_INQUIRY = 7
    ETISALAT_INQUIRY_BY_REF = 8

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
                "SMSSENDER": "",    # SMSC sender name for the standard vodafone users
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
        elif purpose == self.DISBURSEMENT_OR_CHANGE_PROFILE_CALLBACK_INQUIRY:
            data.update({
                "BATCH_ID": "",
                "TYPE": "DISBINQREQ"
            })
        elif purpose == self.ETISALAT_INQUIRY_BY_REF:
            data.update({
                "EXTREFNUM": "",        # MSISDNs List
                "TYPE": "EXTXNRREQ"
            })

        return data

    def _refine_payload_pin(self, payload):
        """Replace payload pin with *"""
        payload_without_pin = copy.deepcopy(payload)
        payload_without_pin['PIN'] = '******' if payload_without_pin.get('PIN', False) else False

        return payload_without_pin

    def accumulate_bulk_disbursement_payload(self, agents_attr, consumers_attr, sms_sender_name=''):
        """
        :param agents_attr: Agents list along with their pins that will make the disbursement action
        :param consumers_attr: Consumers of the e-money
        :param sms_sender_name: SMSC sender name for the standard vodafone users
        :return: bulk disbursement request payload, refined payload without pin to be logged
        """
        if not all([agents_attr, consumers_attr]):
            raise ValueError(_("Agents and consumers are required parameters for the bulk disbursement dictionary"))

        payload = self.return_vmt_data(self.DISBURSEMENT)
        payload.update({
            'SENDERS': agents_attr,
            'RECIPIENTS': consumers_attr,
            'SMSSENDER': sms_sender_name
        })
        if not sms_sender_name:
            del(payload["SMSSENDER"])

        payload_without_pin = copy.deepcopy(payload)
        for internal_agent_dictionary in payload_without_pin['SENDERS']:
            internal_agent_dictionary['PIN'] = '******'

        return payload, payload_without_pin

    def accumulate_instant_disbursement_payload(self,
                                                agent_attr,
                                                consumer_attr,
                                                amount_attr,
                                                raw_pin_attr,
                                                issuer_attr):
        """
        :param agent_attr: Agent that will send/disburse the money
        :param consumer_attr: Consumers of the e-money
        :param amount_attr: Amount to be disbursed
        :param issuer_attr: Wallet issuer channel that the e-money will be disbursed over
        :return: instant disbursement request payload, refined payload without pin to be logged
        """
        valid_issuers_list = ['vodafone', 'etisalat']

        if not all([agent_attr, consumer_attr, amount_attr, raw_pin_attr, issuer_attr]):
            if str(issuer_attr).lower() not in valid_issuers_list:
                raise ValueError(_("Parameters' values are not proper for the instant disbursement dictionary"))

        payload = self.return_vmt_data(self.INSTANT_DISBURSEMENT)
        payload.update({
            'WALLETISSUER': issuer_attr.upper(),
            'MSISDN': agent_attr,
            'MSISDN2': consumer_attr,
            'AMOUNT': amount_attr,
            'PIN': raw_pin_attr
        })

        return payload, self._refine_payload_pin(payload)

    def accumulate_change_profile_payload(self, users_attr, new_profile_attr):
        """
        :param users_attr: MSISDNs which we want to change their fees profiles
        :param new_profile_attr: the new profile to be assigned to the MSISDNs
        :return: change profile request payload
        """
        if not all([users_attr, new_profile_attr]):
            raise ValueError(_("MSISDNS and a new profile are required parameters for the change profile dictionary"))

        payload = self.return_vmt_data(self.CHANGE_PROFILE)
        payload.update({
            'USERS': users_attr,
            'NEWPROFILE': new_profile_attr
        })
        return payload

    def accumulate_set_pin_payload(self, users_attr, pin_attr):
        """
        :param users_attr: MSISDNs which we want to set their pins
        :param pin_attr: the raw pin
        :return: set pin request payload
        """
        if not all([users_attr, pin_attr]):
            raise ValueError(_("MSISDNS and a pin are required parameters for the set pin dictionary"))

        payload = self.return_vmt_data(self.SET_PIN)
        payload.update({
            'USERS': users_attr,
            'PIN': pin_attr
        })

        return payload, self._refine_payload_pin(payload)

    def accumulate_user_inquiry_payload(self, users_attr):
        """
        :param users_attr: Agents/MSISDNs to be on-boarded so we have to make sure they're active and have no pins
        :return: user inquiry request payload
        """
        if not users_attr:
            raise ValueError(_("Agents are required parameter for the user inquiry dictionary"))

        payload = self.return_vmt_data(self.USER_INQUIRY)
        payload.update({'USERS': users_attr})
        return payload

    def accumulate_balance_inquiry_payload(self, super_agent_attr, pin_attr):
        """
        :param super_agent_attr: super agent user/msisdn
        :param pin_attr: the raw pin
        :return: balance inquiry request payload, refined payload without pin to be logged
        """
        if not super_agent_attr:
            raise ValueError(_("Super agent and a pin are required parameters for the balance inquiry dictionary"))

        payload = self.return_vmt_data(self.BALANCE_INQUIRY)
        payload.update({
            'MSISDN': super_agent_attr,
            'PIN': pin_attr
        })

        return payload, self._refine_payload_pin(payload)

    def accumulate_disbursement_or_change_profile_callback_inquiry_payload(self, batch_id):
        """
        :param batch_id: id returned from the central when making a bulk disbursement or change profile
        :return: bulk disbursement/change profile callback inquiry request payload
        """
        if not batch_id:
            raise ValueError(_("Batch ID parameter is required for the callback inquiry dictionary"))

        payload = self.return_vmt_data(self.DISBURSEMENT_OR_CHANGE_PROFILE_CALLBACK_INQUIRY)
        payload.update({"BATCH_ID": str(batch_id)})
        return payload

    def accumulate_inquiry_for_etisalat_by_ref_id(self, trn_id):
        payload = self.return_vmt_data(self.ETISALAT_INQUIRY_BY_REF)
        payload.update({"EXTREFNUM": trn_id})
        return payload



class AbstractTransactionCurrency(models.Model):
    """
    Abstract class for handling different transaction currency.
    """

    EGYPTIAN_POUND = 'EGP'

    CURRENCY_CHOICES = (
        (EGYPTIAN_POUND, 'Egyptian Pound'),
    )

    currency = models.CharField(_('Currency'), max_length=3, choices=CURRENCY_CHOICES, default=EGYPTIAN_POUND)

    class Meta:
        abstract = True


class AbstractTransactionCategory(models.Model):
    """
    Abstract base class for handling different transaction category codes.
    """

    GENERAL_CASH = 'CASH'
    ONUS_DIRECT_DEBIT = 'LIMA'
    LPRT = 'LPRT'
    MOBILE_PAYMENT = 'MOBI'
    PREPAID = 'PCRD'
    PENSION = 'PENS'
    SALARY = 'SALA'
    USD = 'USD'

    CATEGORY_CHOICES = (
        (GENERAL_CASH, 'General cash'),
        (ONUS_DIRECT_DEBIT, 'Onus direct debit'),
        (LPRT, 'LPRT'),
        (MOBILE_PAYMENT, 'Mobile payment'),
        (PREPAID, 'PrePaid card'),
        (PENSION, 'Payment of pension'),
        (SALARY, 'Payment of salaries'),
        (USD, 'USD transaction')
    )

    category_code = models.CharField(
            _('Category Code'),
            max_length=4,
            choices=CATEGORY_CHOICES,
            default=GENERAL_CASH,
            help_text=_('Type of the sending remittance')
    )

    class Meta:
        abstract = True


class AbstractTransactionPurpose(models.Model):
    """
    Abstract base class for handling different transaction purpose codes.
    """

    CASH_TRANSFER = "CASH"
    INSTALLMENT = "INST"
    PAYROLL = "PAYR"
    SUPPLIER = "SUPP"
    COLLECTION = "COLL"
    CREDIT_CARD = "CCRD"
    COLT = "COLT"
    PENSION = "PENS"
    ACCT = "ACCT"
    SALARY = "SALA"
    OTHER = "OTHR"

    PURPOSE_CHOICES = (
        (CASH_TRANSFER, _("حوالات - Cash Transfer")),
        (INSTALLMENT, _("أقساط - Installment")),
        (PAYROLL, _("مرتبات - Payroll")),
        (SUPPLIER, _("موردين - Supplier Payment")),
        (COLLECTION, _("كمبيالات - Collection")),
        (CREDIT_CARD, _("بطاقة إئتمان - Credit Card")),
        (COLT, _("متحصلات - COLT")),
        (PENSION, _("Transaction is the payment of pension - معاشات - Pension")),
        (ACCT, _("Transaction moves funds between 2 accounts of same account holder")),
        (SALARY, _("Transaction is the payment of salaries")),
        (OTHER, _("Other payment purpose")),
    )

    purpose = models.CharField(
            _('Purpose'),
            max_length=4,
            choices=PURPOSE_CHOICES,
            default=CASH_TRANSFER,
    )

    class Meta:
        abstract = True


class AbstractBaseACHTransactionStatus(models.Model):
    """
    Base ACH Transaction Status model.
    """

    # choices
    SUCCESSFUL = "S"
    RETURNED = "R"
    REJECTED = "J"
    FAILED = "F"
    PENDING = "P"
    DEFAULT = "d"
    STATUS_CHOICES = [
        (SUCCESSFUL, _("Successful")),
        (RETURNED, _("Returned")),
        (REJECTED, _("Rejected")),
        (FAILED, _("Failed")),
        (PENDING, _("Pending")),
        (DEFAULT, _("Default")),
    ]
    status = models.CharField(
            _("status"), max_length=1, choices=STATUS_CHOICES, default=DEFAULT
    )

    class Meta:
        abstract = True
