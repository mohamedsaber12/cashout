from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.utils.validations import phonenumber_form_validate


class InstantUserInquirySerializer(serializers.Serializer):
    """
    Serializes instant user/wallet inquiry requests
    """
    msisdn = serializers.CharField(max_length=11, required=True)
    issuer = serializers.CharField(max_length=12, required=True)
    unique_identifier = serializers.CharField(max_length=255, required=True)

    def validate(self, attrs):
        """
        Validate the request attributes
        :param attrs:
        :return:
        """
        msisdn = f"+2{attrs.get('msisdn')}"
        issuer = attrs.get("issuer")
        unique_identifier = attrs.get("unique_identifier")

        # Validate that the issuer is VodafoneCash
        if issuer != "VodafoneCash":
            msg = _("You are not permitted to inquire at an issuer other that 'VodafoneCash'")
            raise serializers.ValidationError(msg)

        # Validate wallet number is a valid EG phone number
        try:
            phonenumber_form_validate(msisdn)
        except ValidationError as e:
            msg = _("Invalid default region")
            raise serializers.ValidationError(msg)

        # Validate unique issuer

        return attrs
