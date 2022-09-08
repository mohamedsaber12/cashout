from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.utils.validations import phonenumber_form_validate
from disbursement.utils import (
    VALID_BANK_CODES_LIST, VALID_BANK_TRANSACTION_TYPES_LIST, VALID_BANK_IMD_BIN_LIST
)


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


def issuer_validator(issuer):
    """
    Validate that the issuer being used is VodafoneCash
    :param issuer: the type of wallet to check
    :return:
    """
    if issuer != "VodafoneCash":
        msg = _("You are not permitted to inquire at an issuer other that 'VodafoneCash'")
        raise serializers.ValidationError(msg)


def fees_validator(fees):
    """
    Validate that the fees -if any- is one of ['Full', 'Half', 'No fees']
    :param fees: is the applied charge to use the this service
    :return:
    """
    fees_values = ["Full", "Half", "No fees"]

    if fees is not None and fees not in fees_values:
        msg = _("The fee flag passed to be applied is incorrect, please pass one of ['Full', 'Half', 'No fees']")
        raise serializers.ValidationError(msg)


def cashin_issuer_validator(issuer):
    """
    Validate that the cashin issuer being used is one of the valid issuers
    :param issuer: The way that the consumer will use
    :return: If valid it just will return the passed issuer value if not it'll raise validation error
    """
    cashin_valid_issuers_list = ["vodafone", "etisalat", "orange", "aman", "bank_wallet", "bank_card"]

    if issuer.lower() not in cashin_valid_issuers_list:
        msg = _(f"The passed issuer is not valid, please make sure that the passed issuer value is one of"
                f" {cashin_valid_issuers_list} and try again!")
        raise serializers.ValidationError(msg)


def bank_code_validator(bank_code):
    """
    """
    if str(bank_code).upper() not in VALID_BANK_CODES_LIST:
        msg = _(f"The passed bank code is not valid, please make sure that the passed code value is one of"
                f" {VALID_BANK_CODES_LIST} and try again!")
        raise serializers.ValidationError(msg)

def bank_imd_bin_validator(bank_imd_or_bin):
    """
    validate on imd/bin of pakistan banks
    """
    if str(bank_imd_or_bin) not in VALID_BANK_IMD_BIN_LIST:
        msg = _(f"The passed bank IMD/BIN of acquiring bank is not valid, please make sure that the passed IMD/BIN "
                f"value is one of {VALID_BANK_IMD_BIN_LIST} and try again!")
        raise serializers.ValidationError(msg)

def bank_transaction_type_validator(transaction_type):
    """
    """

    if str(transaction_type).upper() not in VALID_BANK_TRANSACTION_TYPES_LIST:
        msg = _(f"The passed bank transaction type is not valid, please make sure that the passed type value is one of"
                f" {VALID_BANK_TRANSACTION_TYPES_LIST} and try again!")
        raise serializers.ValidationError(msg)
