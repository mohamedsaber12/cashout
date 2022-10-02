# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal

from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from core.models import AbstractBaseStatus
from disbursement.models import BankTransaction

from ..models import AbstractBaseIssuer, InstantTransaction
from .fields import CustomChoicesField, UUIDListField, CardNumberField
from .validators import (
    bank_name_validator, cashin_issuer_validator,
    fees_validator, issuer_validator, msisdn_validator,
    bank_imd_bin_validator
)

from utilities.models.abstract_models import AbstractBaseACHTransactionStatus
import uuid


class InstantDisbursementRequestSerializer(serializers.Serializer):
    """
    Serializes instant disbursement requests
    Notes:
        * amount field:
            - max amount value that can be disbursed at a time is 10,000 EG
            - decimal places allowed at the cases of decimals is for only 2 digits ex: 356.98 EG
            - max number of digits allowed is 7 digits 10,000.00
    """
    issuer = serializers.CharField(required=True, validators=[cashin_issuer_validator])
    msisdn = serializers.CharField(max_length=11, required=False, allow_blank=False, validators=[msisdn_validator])
    bank_card_number = CardNumberField(required=False, allow_blank=False)
    amount = serializers.DecimalField(
        required=True,
        decimal_places=2,
        max_digits=9,
        min_value=Decimal(1.0)
    )
    fees = serializers.CharField(
        max_length=4,
        required=False,
        allow_blank=True,
        allow_null=True,
        validators=[fees_validator]
    )
    full_name = serializers.CharField(max_length=254, required=False, allow_blank=False)
    bank_name = serializers.CharField(
        max_length=254, required=False, allow_blank=False, validators=[bank_name_validator]
    )
    pin = serializers.CharField(min_length=6, max_length=6, required=False, allow_null=True, allow_blank=True)
    user = serializers.CharField(max_length=254, required=False, allow_blank=False)
    is_single_step = serializers.BooleanField(required=False, default=False)
    client_reference_id = serializers.UUIDField(required=False)
    comment = serializers.CharField(max_length=140, required=False)

    def validate(self, attrs):
        """Validate Aman issuer needed attributes"""
        issuer = str(attrs.get('issuer', '')).lower()
        msisdn = attrs.get('msisdn', '')
        bank_card_number = attrs.get('bank_card_number', '')
        full_name = attrs.get('full_name', '')
        bank_name = attrs.get('bank_name', '')

        if attrs.get('client_reference_id'):
            if InstantTransaction.objects.filter(client_transaction_reference=attrs.get('client_reference_id')).exists():
                raise serializers.ValidationError(
                    _("client_reference_id is used before.")
                )

        if issuer in ["jazzcash", "easypaisa", "zong", "sadapay", "ubank",
                      "bykea", "simpaisa", "tag", "opay"]:
            if not msisdn:
                raise serializers.ValidationError(
                    _("You must pass valid msisdn")
                )

        elif issuer == 'bank_wallet':
            if not msisdn:
                raise serializers.ValidationError(
                    _("You must pass valid msisdn")
                )
            if not bank_name:
                raise serializers.ValidationError(
                    _("You must pass valid bank name")
                )

        elif issuer == 'bank_card':
            if not bank_name or not bank_card_number:
                raise serializers.ValidationError(
                    _("You must pass valid values for fields [bank_name, bank_card_number]")
                )
            if any(e in str(full_name) for e in '!%*+&,<=>'):
                raise serializers.ValidationError(
                    _("Symbols like !%*+&,<=> not allowed in full_name")
                )

        return attrs


class BankTransactionResponseModelSerializer(serializers.ModelSerializer):
    """
    Serializes the response of instant bank transaction objects
    """

    transaction_id = serializers.SerializerMethodField()
    issuer = serializers.SerializerMethodField()
    disbursement_status = CustomChoicesField(source='status', choices=AbstractBaseACHTransactionStatus.STATUS_CHOICES)
    status_code = serializers.SerializerMethodField()
    status_description = serializers.SerializerMethodField()
    bank_card_number = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    bank_name = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    def get_transaction_id(self, transaction):
        """Retrieves parent transaction transaction_id"""
        return transaction.uid

    def get_issuer(self, transaction):
        """Retrieves transaction issuer"""
        return "bank_card"

    def get_status_code(self, transaction):
        """Retrieves transaction status code"""
        return transaction.transaction_status_code

    def get_status_description(self, transaction):
        """Retrieves transaction status description"""
        return transaction.transaction_status_description

    def get_bank_card_number(self, transaction):
        """Retrieves bank card number"""
        return transaction.anon_recipient

    def get_full_name(self, transaction):
        """Retrieves transaction recipient name"""
        return transaction.recipient_name

    def get_bank_name(self, transaction):
        """Retrieves transaction cashing details"""
        return transaction.creditor_bank_name

    def get_created_at(self, transaction):
        """Retrieves transaction created_at time formatted"""
        return transaction.created_at.strftime("%Y-%m-%d %H:%M:%S.%f")

    def get_updated_at(self, transaction):
        """Retrieves transaction updated_at time formatted"""
        return transaction.updated_at.strftime("%Y-%m-%d %H:%M:%S.%f")

    class Meta:
        model = InstantTransaction
        fields = [
            'transaction_id', 'issuer', 'amount', 'bank_card_number', 'full_name', 'bank_name',
            'disbursement_status', 'status_code', 'status_description', 'client_transaction_reference',
            'created_at', 'updated_at'
        ]


class InstantTransactionResponseModelSerializer(serializers.ModelSerializer):
    """
    Serializes the response of instant transactions
    """

    transaction_id = serializers.SerializerMethodField()
    issuer = CustomChoicesField(source='issuer_type', choices=AbstractBaseIssuer.ISSUER_TYPE_CHOICES)
    msisdn = serializers.SerializerMethodField()
    disbursement_status = CustomChoicesField(
        source='status', choices=[
            *AbstractBaseStatus.STATUS_CHOICES,
            ("U", _("Unknown")),
        ]
    )
    status_code = serializers.SerializerMethodField()
    status_description = serializers.SerializerMethodField()
    bank_name = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    def get_transaction_id(self, transaction):
        """Retrieves transaction id"""
        return transaction.uid

    def get_msisdn(self, transaction):
        """Retrieves transaction recipient"""
        return transaction.anon_recipient

    def get_status_code(self, transaction):
        """Retrieves transaction status code"""
        return transaction.transaction_status_code

    def get_status_description(self, transaction):
        """Retrieves transaction status description"""
        return transaction.transaction_status_description

    def get_bank_name (self, transaction):
        """Retrieves transaction bank name"""
        if transaction.issuer == InstantTransaction.BANK_WALLET:
            return transaction.creditor_bank_name
        return ""

    def get_created_at(self, transaction):
        """Retrieves transaction created_at time formatted"""
        return transaction.created_at.strftime("%Y-%m-%d %H:%M:%S.%f")

    def get_updated_at(self, transaction):
        """Retrieves transaction updated_at time formatted"""
        return transaction.updated_at.strftime("%Y-%m-%d %H:%M:%S.%f")

    class Meta:
        model = InstantTransaction
        fields = [
            'transaction_id', 'issuer', 'msisdn', 'amount', 'disbursement_status', 'status_code',
            'status_description', 'bank_name', 'client_transaction_reference',  'created_at', 'updated_at'
        ]


class BulkInstantTransactionReadSerializer(serializers.Serializer):
    """
    Serializes the bulk transaction inquiry request, list of uuid4 inputs
    """

    transactions_ids_list = UUIDListField(required=True, allow_null=False, allow_empty=False)

class InstantUserInquirySerializer(serializers.Serializer):
    """
    Serializes instant user/wallet inquiry requests
    """
    msisdn = serializers.CharField(max_length=11, required=True, validators=[msisdn_validator])
    issuer = serializers.CharField(max_length=12, required=True, validators=[issuer_validator])
    unique_identifier = serializers.CharField(max_length=255, required=True)    # Add validations/rate limit


class CancelAmanTransactionSerializer(serializers.Serializer):

    transaction_id = serializers.UUIDField(required=True)
