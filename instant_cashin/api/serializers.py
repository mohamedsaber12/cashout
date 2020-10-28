# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from core.models import AbstractBaseStatus
from disbursement.models import BankTransaction

from ..models import AbstractBaseIssuer, InstantTransaction
from .fields import CustomChoicesField, UUIDListField, CardNumberField
from .validators import (
    bank_code_validator, cashin_issuer_validator,
    fees_validator, issuer_validator, msisdn_validator, bank_transaction_type_validator,
)


class InstantDisbursementRequestSerializer(serializers.Serializer):
    """
    Serializes instant disbursement requests
    Notes:
        * amount field:
            - max amount value that can be disbursed at a time is 10,000 EG
            - decimal places allowed at the cases of decimals is for only 2 digits ex: 356.98 EG
            - max number of digits allowed is 7 digits 10,000.00
    """
    amount = serializers.DecimalField(required=True, decimal_places=2, max_digits=7)
    issuer = serializers.CharField(required=True, validators=[cashin_issuer_validator])
    msisdn = serializers.CharField(max_length=11, required=False, allow_blank=False, validators=[msisdn_validator])
    bank_code = serializers.CharField(max_length=4, required=False, allow_blank=False, validators=[bank_code_validator])
    bank_card_number = CardNumberField(required=False, allow_blank=False)
    bank_transaction_type = serializers.CharField(
            min_length=6,
            max_length=13,
            required=False,
            allow_blank=False,
            validators=[bank_transaction_type_validator]
    )
    fees = serializers.CharField(
            max_length=4,
            required=False,
            allow_blank=True,
            allow_null=True,
            validators=[fees_validator]
    )
    full_name = serializers.CharField(max_length=254, required=False, allow_blank=False)
    first_name = serializers.CharField(max_length=254, required=False)
    last_name = serializers.CharField(max_length=254, required=False)
    email = serializers.EmailField(max_length=254, required=False)
    pin = serializers.CharField(min_length=6, max_length=6, required=False, allow_null=True, allow_blank=True)

    def validate(self, attrs):
        """Validate Aman issuer needed attributes"""
        issuer = str(attrs.get('issuer', '')).lower()
        msisdn = attrs.get('msisdn', '')
        first_name = attrs.get('first_name', '')
        last_name = attrs.get('last_name', '')
        email = attrs.get('email', '')
        bank_code = attrs.get('bank_code', '')
        bank_card_number = attrs.get('bank_card_number', '')
        bank_transaction_type = attrs.get('bank_transaction_type', '')
        full_name = attrs.get('full_name', '')

        if issuer in ['vodafone', 'etisalat']:
            if not msisdn:
                raise serializers.ValidationError(
                        _("You must pass valid msisdn")
                )
        elif issuer == 'aman':
            if not msisdn or not first_name or not last_name or not email:
                raise serializers.ValidationError(
                        _("You must pass valid values for fields [first_name, last_name, email]")
                )
        elif issuer == 'bank_card':
            if not bank_code or not bank_card_number or not bank_transaction_type or not full_name:
                raise serializers.ValidationError(
                        _("You must pass valid values for fields [bank_code, bank_card_number, bank_transaction_type, "
                          "full_name]")
                )
        elif issuer in ['bank_wallet', 'orange']:
            if not msisdn or not full_name:
                raise serializers.ValidationError(
                        _("You must pass valid values for fields [msisdn, full_name]")
                )

        return attrs


class BankTransactionResponseModelSerializer(serializers.ModelSerializer):
    """
    Serializes the response of instant bank transaction objects
    """

    transaction_id = serializers.SerializerMethodField()
    issuer = serializers.SerializerMethodField()
    disbursement_status = CustomChoicesField(source='status', choices=AbstractBaseStatus.STATUS_CHOICES)
    status_code = serializers.SerializerMethodField()
    status_description = serializers.SerializerMethodField()
    bank_card_number = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    bank_code = serializers.SerializerMethodField()
    bank_transaction_type = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    def get_transaction_id(self, transaction):
        """Retrieves parent transaction transaction_id"""
        return transaction.parent_transaction.transaction_id

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
        return transaction.creditor_account_number

    def get_full_name(self, transaction):
        """Retrieves transaction recipient name"""
        return transaction.creditor_name

    def get_bank_code(self, transaction):
        """Retrieves transaction cashing details"""
        return transaction.creditor_bank

    def get_bank_transaction_type(self, transaction):
        """Retrieves transaction type"""
        if transaction.purpose == "SALA":
            bank_transaction_type = "salary"
        elif transaction.purpose == "PENS":
            bank_transaction_type = "pension"
        elif transaction.purpose == "CCRD":
            bank_transaction_type = "credit_card"
        elif transaction.category_code == "PCRD":
            bank_transaction_type = "prepaid"
        else:
            bank_transaction_type = "cash_transfer"

        return bank_transaction_type

    def get_created_at(self, transaction):
        """Retrieves transaction created_at time formatted"""
        return transaction.parent_transaction.created_at.strftime("%Y-%m-%d %H:%M:%S.%f")

    def get_updated_at(self, transaction):
        """Retrieves transaction updated_at time formatted"""
        return transaction.updated_at.strftime("%Y-%m-%d %H:%M:%S.%f")

    class Meta:
        model = BankTransaction
        fields = [
            'transaction_id', 'issuer', 'amount', 'bank_card_number', 'full_name', 'bank_code', 'bank_transaction_type',
            'disbursement_status', 'status_code', 'status_description', 'created_at', 'updated_at'
        ]


class InstantTransactionResponseModelSerializer(serializers.ModelSerializer):
    """
    Serializes the response of instant transactions
    """

    transaction_id = serializers.SerializerMethodField()
    issuer = CustomChoicesField(source='issuer_type', choices=AbstractBaseIssuer.ISSUER_TYPE_CHOICES)
    msisdn = serializers.SerializerMethodField()
    disbursement_status = CustomChoicesField(source='status', choices=AbstractBaseStatus.STATUS_CHOICES)
    status_code = serializers.SerializerMethodField()
    status_description = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    aman_cashing_details = serializers.SerializerMethodField()
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

    def get_full_name(self, transaction):
        """Retrieves transaction recipient name"""
        return transaction.recipient_name

    def get_aman_cashing_details(self, transaction):
        """Retrieves aman cashing details of aman channel transaction"""
        aman_cashing_details = transaction.aman_transaction

        if aman_cashing_details:
            return {
                'bill_reference': aman_cashing_details.bill_reference,
                'is_paid': aman_cashing_details.is_paid
            }

    def get_created_at(self, transaction):
        """Retrieves transaction created_at time formatted"""
        return transaction.created_at.strftime("%Y-%m-%d %H:%M:%S.%f")

    def get_updated_at(self, transaction):
        """Retrieves transaction updated_at time formatted"""
        return transaction.updated_at.strftime("%Y-%m-%d %H:%M:%S.%f")

    class Meta:
        model = InstantTransaction
        fields = [
            'transaction_id', 'issuer', 'msisdn', 'amount', 'full_name', 'disbursement_status', 'status_code',
            'status_description', 'aman_cashing_details', 'created_at', 'updated_at'
        ]


class BulkInstantTransactionReadSerializer(serializers.Serializer):
    """
    Serializes the bulk transaction inquiry request, list of uuid4 inputs
    """

    transactions_ids_list = UUIDListField(required=True, allow_null=False, allow_empty=False)
    bank_transactions = serializers.BooleanField(default=False)


class InstantUserInquirySerializer(serializers.Serializer):
    """
    Serializes instant user/wallet inquiry requests
    """
    msisdn = serializers.CharField(max_length=11, required=True, validators=[msisdn_validator])
    issuer = serializers.CharField(max_length=12, required=True, validators=[issuer_validator])
    unique_identifier = serializers.CharField(max_length=255, required=True)    # Add validations/rate limit
