from rest_framework import serializers

from .validators import msisdn_validator, issuer_validator


class InstantUserInquirySerializer(serializers.Serializer):
    """
    Serializes instant user/wallet inquiry requests
    """
    msisdn = serializers.CharField(max_length=11, required=True, validators=[msisdn_validator])
    issuer = serializers.CharField(max_length=12, required=True, validators=[issuer_validator])
    unique_identifier = serializers.CharField(max_length=255, required=True)    # Add validations/rate limit
