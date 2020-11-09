# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin


INSTANT_TRX_RECEIVED = "Transaction received and validated successfully. Dispatched for being processed by the carrier"
INSTANT_TRX_BEING_PROCESSED = "Transaction received by the carrier and being processed now"
INSTANT_TRX_IS_ACCEPTED = "Transaction processed and accepted by the carrier. Your transfer is ready for exchanging now"
INSTANT_TRX_IS_REJECTED = "Transaction rejected by the carrier. Please try again or contact your support team"
BANK_TRX_RECEIVED = "Transaction received and validated successfully. Dispatched for being processed by the bank"
BANK_TRX_BEING_PROCESSED = "Transaction received by the bank and being processed now"
BANK_TRX_IS_ACCEPTED = "Transaction processed and accepted by the bank. Your transfer is ready for exchanging now"
INTERNAL_ERROR_MSG = "Process stopped during an internal error, can you try again or contact your support team"
EXTERNAL_ERROR_MSG = "Process stopped during an external error, can you try again or contact your support team"


VALID_BANK_CODES_LIST = [
    "AUB",
    "CITI",
    "MIDB",
    "BDC",
    "HSBC",
    "CAE",
    "EGB",
    "UB",
    "QNB",
    "BBE",
    "ARAB",
    "ENBD",
    "ABK",
    "NBK",
    "ABC",
    "FAB",
    "ADIB",
    "CIB",
    "HDB",
    "MISR",
    "AAIB",
    "EALB",
    "EDBE",
    "FAIB",
    "BLOM",
    "ADCB",
    "BOA",
    "SAIB",
    "NBE",
    "ABRK",
    "POST",
    "NSB",
    "IDB",
    "SCB",
    "MASH",
    "AIB",
    "AUDI",
    "GASC",
    "EGPA",
    "ARIB",
    "PDAC",
    "NBG",
    "CBE"
]

VALID_BANK_TRANSACTION_TYPES_LIST = [
    "CASH_TRANSFER",
    "SALARY",
    "PENSION",
    "PREPAID",
    "CREDIT_CARD"
]

TRX_RETURNED_BY_BANK_CODES = [
    "000100", "000101", "000102", "000103", "000104", "000105", "000106", "000107", "000108", "000109", "000110",
    "000111", "000112"
]

TRX_REJECTED_BY_BANK_CODES = [
    "000001", "000002", "000003", "000004", "000005", "000006", "000007", "000008", "000009", "000010", "000011",
    "000012", "000013", "000014"
]


def custom_titled_filter(title):
    """
    Function for changing field's filter title at the django admin
    :param title: the new title to be viewed
    """
    class Wrapper(admin.FieldListFilter):
        def __new__(cls, *args, **kwargs):
            instance = admin.FieldListFilter.create(*args, **kwargs)
            instance.title = title
            return instance
    return Wrapper
