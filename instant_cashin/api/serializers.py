from django.utils.translation import ugettext_lazy as _

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
    Notes:
        * amount field:
            - max amount value that can be disbursed at a time is 10,000 EG
            - decimal places allowed at the cases of decimals is for only 2 digits ex: 356.98 EG
            - max number of digits allowed is 7 digits 10,000.00
    """
    msisdn = serializers.CharField(max_length=11, required=True, validators=[msisdn_validator])
    amount = serializers.DecimalField(required=True, max_value=10000, decimal_places=2, max_digits=7)
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
