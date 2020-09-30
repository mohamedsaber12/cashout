# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from core.models import AbstractBaseStatus

from ..models import AbstractBaseIssuer, InstantTransaction
from .fields import CustomChoicesField, UUIDListField, CardNumberField
from .validators import (
    bank_code_validator, cashin_issuer_validator,
    fees_validator, issuer_validator, msisdn_validator, bank_transaction_type_validator,
)


class InstantUserInquirySerializer(serializers.Serializer):
    """
    Serializes instant user/wallet inquiry requests
    """
    msisdn = serializers.CharField(max_length=11, required=True, validators=[msisdn_validator])
    issuer = serializers.CharField(max_length=12, required=True, validators=[issuer_validator])
    unique_identifier = serializers.CharField(max_length=255, required=True)    # Add validations/rate limit


class InstantDisbursementSerializer(serializers.Serializer):
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

        if issuer in ['vodafone', 'etisalat', 'orange']:
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
        elif issuer == 'bank_wallet':
            if not bank_card_number or not bank_transaction_type or not full_name:
                raise serializers.ValidationError(
                        _("You must pass valid values for fields [bank_code, bank_card_number, bank_transaction_type, "
                          "full_name]")
                )

        return attrs


class BulkInstantTransactionReadSerializer(serializers.Serializer):
    """
    Serializes the bulk transaction inquiry request, list of uuid4 inputs
    """

    transactions_ids_list = UUIDListField()


class InstantTransactionWriteModelSerializer(serializers.ModelSerializer):
    """
    Serializes the bulk transaction inquiry response, list of instant transaction objects
    """

    transaction_status = CustomChoicesField(source='status', choices=AbstractBaseStatus.STATUS_CHOICES)
    channel = CustomChoicesField(source='issuer_type', choices=AbstractBaseIssuer.ISSUER_TYPE_CHOICES)
    transaction_id = serializers.SerializerMethodField()
    msisdn = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    aman_cashing_details = serializers.SerializerMethodField()

    def get_aman_cashing_details(self, transaction):
        """Retrieves aman cashing details of aman channel transaction"""
        aman_cashing_details = transaction.aman_transaction

        if aman_cashing_details:
            return {
                'bill_reference': aman_cashing_details.bill_reference,
                'is_paid': aman_cashing_details.is_paid
            }

    def get_transaction_id(self, transaction):
        """Retrieves transaction id"""
        return transaction.uid

    def get_msisdn(self, transaction):
        """Retrieves transaction consumer"""
        return transaction.anon_recipient

    def get_created_at(self, transaction):
        """Retrieves transaction created_at time formatted"""
        return transaction.created_at.strftime("%Y-%m-%d %H:%M:%S.%f")

    def get_updated_at(self, transaction):
        """Retrieves transaction updated_at time formatted"""
        return transaction.updated_at.strftime("%Y-%m-%d %H:%M:%S.%f")

    class Meta:
        model = InstantTransaction
        fields = [
            'transaction_id', 'transaction_status', 'channel', 'msisdn', 'amount', 'failure_reason',
            'created_at', 'updated_at', 'aman_cashing_details'
        ]
