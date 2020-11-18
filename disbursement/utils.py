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

BANK_CODES = [
    {"name": "Ahli United Bank"                           , "code":  "AUB"},
    {"name": "Citi Bank N.A. Egypt"                       , "code":  "CITI"},
    {"name": "MIDBANK"                                    , "code":  "MIDB"},
    {"name": "Banque Du Caire"                            , "code":  "BDC"},
    {"name": "HSBC Bank Egypt S.A.E"                      , "code":  "HSBC"},
    {"name": "Credit Agricole Egypt S.A.E"                , "code":  "CAE"},
    {"name": "Egyptian Gulf Bank"                         , "code":  "EGB"},
    {"name": "The United Bank"                            , "code":  "UB"},
    {"name": "Qatar National Bank Alahli"                 , "code":  "QNB"},
    {"name": "Central Bank Of Egypt"                      , "code":  "BBE"},
    {"name": "Arab Bank PLC"                              , "code":  "ARAB"},
    {"name": "Emirates National Bank of Dubai"            , "code":  "ENBD"},
    {"name": "Al Ahli Bank of Kuwait – Egypt"             , "code":  "ABK"},
    {"name": "National Bank of Kuwait – Egypt"            , "code":  "NBK"},
    {"name": "Arab Banking Corporation - Egypt S.A.E"     , "code":  "ABC"},
    {"name": "First Abu Dhabi Bank"                       , "code":  "FAB"},
    {"name": "Abu Dhabi Islamic Bank – Egypt"             , "code":  "ADIB"},
    {"name": "Commercial International Bank - Egypt S.A.E", "code":  "CIB"},
    {"name": "Housing And Development Bank"               , "code":  "HDB"},
    {"name": "Banque Misr"                                , "code":  "MISR"},
    {"name": "Arab African International Bank"            , "code":  "AAIB"},
    {"name": "Egyptian Arab Land Bank"                    , "code":  "EALB"},
    {"name": "Export Development Bank of Egypt"           , "code":  "EDBE"},
    {"name": "Faisal Islamic Bank of Egypt"               , "code":  "FAIB"},
    {"name": "Blom Bank"                                  , "code":  "BLOM"},
    {"name": "Abu Dhabi Commercial Bank – Egypt"          , "code":  "ADCB"},
    {"name": "Alex Bank Egypt"                            , "code":  "BOA"},
    {"name": "Societe Arabe Internationale De Banque"     , "code":  "SAIB"},
    {"name": "National Bank of Egypt"                     , "code":  "NBE"},
    {"name": "Al Baraka Bank Egypt B.S.C."                , "code":  "ABRK"},
    {"name": "Egypt Post"                                 , "code":  "POST"},
    {"name": "Nasser Social Bank"                         , "code":  "NSB"},
    {"name": "Industrial Development Bank"                , "code":  "IDB"},
    {"name": "Suez Canal Bank"                            , "code":  "SCB"},
    {"name": "Mashreq Bank"                               , "code":  "MASH"},
    {"name": "Arab Investment Bank"                       , "code":  "AIB"},
    {"name": "Audi Bank"                                  , "code":  "AUDI"},
    {"name": "General Authority For Supply Commodities"   , "code":  "GASC"},
    {"name": "National Bank of Egypt - EGPA"              , "code":  "EGPA"},
    {"name": "Arab International Bank"                    , "code":  "ARIB"},
    {"name": "Agricultural Bank of Egypt"                 , "code":  "PDAC"},
    {"name": "National Bank of Greece"                    , "code":  "NBG"},
    {"name": "Central Bank Of Egypt"                      , "code":  "CBE"}
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


def determine_trx_category_and_purpose(transaction_type):
    """Determine transaction category code and purpose based on the passed transaction_type"""
    if transaction_type.upper() == "MOBILE":
        category_purpose_dict = {
            "category_code": "MOBI",
            "purpose": "CASH"
        }
    elif transaction_type.upper() == "SALARY":
        category_purpose_dict = {
            "category_code": "CASH",
            "purpose": "SALA"
        }
    elif transaction_type.upper() == "PENSION":
        category_purpose_dict = {
            "category_code": "PENS",
            "purpose": "PENS"
        }
    elif transaction_type.upper() == "PREPAID":
        category_purpose_dict = {
            "category_code": "PCRD",
            "purpose": "CASH"
        }
    elif transaction_type.upper() == "CREDIT_CARD":
        category_purpose_dict = {
            "category_code": "CASH",
            "purpose": "CCRD"
        }
    else:
        category_purpose_dict = {
            "category_code": "CASH",
            "purpose": "CASH"
        }

    return category_purpose_dict
