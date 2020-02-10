from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.utils.validations import phonenumber_form_validate


def msisdn_validator(msisdn):
    """
    Validator for the wallet to consume the cash in
    :param msisdn: the wallet/phone-number being inquired at
    :return:
    """
    msisdn = f"+2{msisdn}"

    try:
        phonenumber_form_validate(msisdn)
    except ValidationError:
        msg = _("Invalid phone number")
        raise serializers.ValidationError(msg)

    return msisdn


def issuer_validator(issuer):
    """
    Validate that the issuer being used is VodafoneCash
    :param issuer: the type of wallet to check
    :return:
    """
    if issuer != "VodafoneCash":
        msg = _("You are not permitted to inquire at an issuer other that 'VodafoneCash'")
        raise serializers.ValidationError(msg)

    return issuer
