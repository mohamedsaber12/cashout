from rest_framework import serializers

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
    """
    msisdn = serializers.CharField(max_length=11, required=True, validators=[msisdn_validator])
    amount = serializers.IntegerField(required=True)
    pin = serializers.CharField(min_length=6, max_length=6, required=False, allow_null=True, allow_blank=True)
    issuer = serializers.CharField(
            max_length=12, required=False, allow_null=True, allow_blank=True, validators=[cashin_issuer_validator]
    )
    fees = serializers.CharField(
            max_length=4, required=False, allow_blank=True, allow_null=True, validators=[fees_validator]
    )
