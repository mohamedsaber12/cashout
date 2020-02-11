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


def fees_validator(fees):
    """
    Validate that the fees -if any- is one of ['Full', 'Half', 'No fees']
    :param fees: is the applied charge to use the this service
    :return:
    """
    fees_values = ["Full", "Half", "No fees"]

    if fees is not None and fees not in fees_values:
        msg = _("The fee flag passed to be applied is incorrect, please pass on of ['Full', 'Half', 'No fees']")
        raise serializers.ValidationError(msg)

    return fees


def user_budget_validator(amount):
    """
    Validate that the amount to be disbursed by this user doesn't exceed his/her account available budget
    :param amount: the amount to be disbursed/cashed in
    :return:
    """
    if amount > 1000:       # To be updated after creating the budget model
        msg = _("Sorry, the amount to be disbursed is exceed you budget limit, please contact your service provider")
        raise serializers.ValidationError(msg)

    return amount
