# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid
from datetime import date
import copy
import logging
from users.models.base_user import User

import requests

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext as _
from django.utils import timezone

from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope, permissions
from rest_framework import status, views
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from disbursement.models import BankTransaction, VMTData
from payouts.settings import TIMEOUT_CONSTANTS
from utilities.logging import logging_message

from ...models import InstantTransaction
from ...specific_issuers_integrations import AmanChannel, OneLinkTransactionsChannel
from ...utils import default_response_structure, get_from_env
from ..mixins import IsInstantAPICheckerUser
from ..serializers import (
    InstantDisbursementRequestSerializer, InstantTransactionResponseModelSerializer,
    BankTransactionResponseModelSerializer
)
from django.conf import settings
from disbursement.utils import BANK_NAME_IMD

INSTANT_CASHIN_SUCCESS_LOGGER = logging.getLogger("instant_cashin_success")
INSTANT_CASHIN_FAILURE_LOGGER = logging.getLogger("instant_cashin_failure")
INSTANT_CASHIN_REQUEST_LOGGER = logging.getLogger("instant_cashin_requests")

INTERNAL_ERROR_MSG = _("Process stopped during an internal error, can you try again or contact your support team")
EXTERNAL_ERROR_MSG = _("Process stopped during an external error, can you try again or contact your support team")
ORANGE_PENDING_MSG = _("Your transaction will be process the soonest, wait for a response at the next 24 hours")
BUDGET_EXCEEDED_MSG = _("Sorry, the amount to be disbursed exceeds you budget limit, please contact your support team")
TIMEOUT_ERROR_MSG = _('Request timeout error')


class InstantDisbursementAPIView(views.APIView):
    """
    Handles instant disbursement/cash_in POST requests
    """

    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope, IsInstantAPICheckerUser]
    throttle_classes = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wallet_issuers = ["jazzcash", "easypaisa", "zong", "sadapay", "ubank",
                               "bykea", "simpaisa", "tag", "opay"]
        self.bank_wallet_issuers = [ "bank_wallet"]
        self.bank_issuers = [ "bank_card"]

    def match_issuer_type(self, issuer):
        """
        Match the wallet issuer used at the request with its corresponding one at the issuer choices
        :param issuer: issuer passed from the serializer
        :return: choice letter that match the issuer type at the model
        """
        for choice in InstantTransaction.ISSUER_TYPE_CHOICES:
            if issuer.lower() == choice[1].lower():
                return choice[0]
        return 'JC'

    def get_imd_from_bank_name(self, bank_name):
        return BANK_NAME_IMD[bank_name]

    def create_instant_transaction_for_bank(self, disburser, serializer):
        """Create instant transaction out of the passed serializer data"""
        amount = serializer.validated_data["amount"]
        issuer = serializer.validated_data["issuer"].lower()
        client_reference_id = serializer.validated_data.get("client_reference_id")
        full_name = serializer.validated_data["full_name"]
        fees, vat = disburser.root.budget.calculate_fees_and_vat_for_amount(
            amount, issuer
        )
        bank_name = serializer.validated_data["bank_name"]
        creditor_account_number = serializer.validated_data["bank_card_number"]

        transaction_dict = {
            "issuer_type": self.match_issuer_type(issuer),
            "currency": "PKR",
            "from_user": disburser,
            "anon_sender": get_from_env("ACCOUNT_NUMBER_FROM"),
            "anon_recipient": creditor_account_number,
            "amount": amount,
            "creditor_bank_imd": self.get_imd_from_bank_name(bank_name),
            "creditor_bank_name": bank_name,
            "status": "P",
            "recipient_name": full_name,
            "disbursed_date": timezone.now(),
            "is_single_step": serializer.validated_data["is_single_step"],
            "client_transaction_reference": client_reference_id,
            "fees": fees,
            "vat": vat,
            "stan": date.today().strftime("%m%d%y"), # generate stan
            "rrn": f"0{str(uuid.uuid4().int)[:11]}", # generate rrn
        }
        instant_transaction = InstantTransaction.objects.create(**transaction_dict)
        return instant_transaction

    def create_instant_transaction_for_wallet(self, disburser, serializer):
        """Create a instant transaction out of the passed serializer data"""
        amount = serializer.validated_data["amount"]
        issuer = serializer.validated_data["issuer"].lower()
        client_reference_id = serializer.validated_data.get("client_reference_id")
        fees, vat = disburser.root.budget.calculate_fees_and_vat_for_amount(
            amount, issuer
        )
        msisdn = serializer.validated_data["msisdn"]

        transaction_dict = {
            "issuer_type": self.match_issuer_type(issuer),
            "currency": "PKR",
            "from_user": disburser,
            "anon_sender": get_from_env("ACCOUNT_NUMBER_FROM"),
            "anon_recipient": msisdn,
            "amount": amount,
            "creditor_bank": "",
            "status": "P",
            "disbursed_date": timezone.now(),
            "is_single_step": serializer.validated_data["is_single_step"],
            "client_transaction_reference": client_reference_id,
            "fees": fees,
            "vat": vat,
            "stan": date.today().strftime("%m%d%y"), # generate stan
            "rrn": f"0{str(uuid.uuid4().int)[:11]}", # generate rrn
        }
        instant_transaction = InstantTransaction.objects.create(**transaction_dict)
        return instant_transaction

    def post(self, request, *args, **kwargs):
        """
        Handles POST HTTP requests
        """
        serializer = InstantDisbursementRequestSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            if 'user' in serializer.validated_data:
                user = User.objects.get(username=serializer.validated_data['user'])
            else:
                user = request.user

            if not user.root.\
                    budget.within_threshold(serializer.validated_data['amount'], serializer.validated_data['issuer']):
                raise ValidationError(BUDGET_EXCEEDED_MSG)
        except (ValidationError, ValueError, Exception) as e:
            if len(serializer.errors) > 0:
                failure_message = serializer.errors
            elif e.args[0] == BUDGET_EXCEEDED_MSG:
                failure_message = BUDGET_EXCEEDED_MSG
            else:
                failure_message = INTERNAL_ERROR_MSG
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[message] [VALIDATION ERROR]", request, e.args)
            return Response({
                "disbursement_status": _("failed"), "status_description": failure_message,
                "status_code": str(status.HTTP_400_BAD_REQUEST)
            }, status=status.HTTP_400_BAD_REQUEST)

        issuer = serializer.validated_data["issuer"].lower()

        try:
            if issuer in self.wallet_issuers:
                instant_trx_obj = self.create_instant_transaction_for_wallet(user, serializer)
            elif issuer in self.bank_wallet_issuers:
                pass
            elif issuer in self.bank_issuers:
                instant_trx_obj = self.create_instant_transaction_for_bank(user, serializer)

            balance_before = balance_after = instant_trx_obj.from_user.root.budget.get_current_balance()
            instant_trx_obj.balance_before = balance_before
            instant_trx_obj.balance_after = balance_after
            instant_trx_obj.save()

        except Exception as e:
            logging_message(INSTANT_CASHIN_FAILURE_LOGGER, "[message] [One Link EXCEPTION]", request, e.args)
            return default_response_structure(
                transaction_id=None, status_description={"Internal Error": INTERNAL_ERROR_MSG},
                field_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, response_status_code=status.HTTP_200_OK
            )

        return OneLinkTransactionsChannel.send_transaction(instant_trx_obj)


class SingleStepDisbursementAPIView(InstantDisbursementAPIView):

    permission_classes = []
