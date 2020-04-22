# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid

from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from core.models import AbstractBaseStatus

from ..models import AbstractBaseIssuer, InstantTransaction
from .fields import CustomChoicesField
from .validators import cashin_issuer_validator, fees_validator, issuer_validator, msisdn_validator


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
    msisdn = serializers.CharField(max_length=11, required=True, validators=[msisdn_validator])
    amount = serializers.DecimalField(required=True, decimal_places=2, max_digits=7)
    pin = serializers.CharField(min_length=6, max_length=6, required=False, allow_null=True, allow_blank=True)
    issuer = serializers.CharField(
            required=True,
            validators=[cashin_issuer_validator]
    )
    fees = serializers.CharField(
            max_length=4,
            required=False,
            allow_blank=True,
            allow_null=True,
            validators=[fees_validator]
    )
    first_name = serializers.CharField(max_length=254, required=False)
    last_name = serializers.CharField(max_length=254, required=False)
    email = serializers.EmailField(max_length=254, required=False)

    def validate(self, attrs):
        """Validate Aman issuer needed attributes"""
        issuer = attrs.get('issuer', '')
        first_name = attrs.get('first_name', '')
        last_name = attrs.get('last_name', '')
        email = attrs.get('email', '')

        if issuer == 'AMAN':
            if not first_name or not last_name or not email:
                raise serializers.ValidationError(
                        _("You must pass valid values for fields [first_name, last_name, email]")
                )

        return attrs


class InstantTransactionReadSerializer(serializers.Serializer):
    """
    """

    transaction_id = serializers.UUIDField(default=uuid.uuid4())


class BulkInstantTransactionReadSerializer(serializers.Serializer):
    """
    """

    ids_list = serializers.ListSerializer(child=InstantTransactionReadSerializer())


class InstantTransactionWriteModelSerializer(serializers.ModelSerializer):
    """
    """

    transaction_status = CustomChoicesField(source='status', choices=AbstractBaseStatus.STATUS_CHOICES)
    channel = CustomChoicesField(source='issuer_type', choices=AbstractBaseIssuer.ISSUER_TYPE_CHOICES)
    transaction_id = serializers.SerializerMethodField()
    msisdn = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    aman_cashing_details = serializers.SerializerMethodField()

    def get_aman_cashing_details(self, transaction):
        """"""
        aman_cashing_details = transaction.aman_transaction.first()

        if aman_cashing_details:
            return {
                'bill_reference': aman_cashing_details.bill_reference,
                'is_paid': aman_cashing_details.is_paid
            }

    def get_transaction_id(self, transaction):
        """"""
        return transaction.uid

    def get_msisdn(self, transaction):
        """"""
        return transaction.anon_recipient

    def get_created_at(self, transaction):
        """"""
        return transaction.created_at.strftime("%Y-%m-%d %H:%M:%S.%f")

    def get_updated_at(self, transaction):
        """"""
        return transaction.updated_at.strftime("%Y-%m-%d %H:%M:%S.%f")

    class Meta:
        model = InstantTransaction
        fields = [
            'transaction_id', 'transaction_status', 'channel', 'msisdn', 'amount', 'failure_reason',
            'created_at', 'updated_at', 'aman_cashing_details'
        ]
