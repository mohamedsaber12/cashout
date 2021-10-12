# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from utilities.models.generic_models import Budget

INSTANT_TRX_RECEIVED = _("Transaction received and validated successfully. Dispatched for being processed by the carrier")
INSTANT_TRX_BEING_PROCESSED = _("Transaction received by the carrier and being processed now")
INSTANT_TRX_IS_ACCEPTED = _("Transaction processed and accepted by the carrier. Your transfer is ready for exchanging now")
INSTANT_TRX_IS_REJECTED = _("Transaction rejected by the carrier. Please try again or contact your support team")
BANK_TRX_RECEIVED = _("Transaction received and validated successfully. Dispatched for being processed by the bank")
BANK_TRX_BEING_PROCESSED = _("Transaction received by the bank and being processed now")
BANK_TRX_IS_SUCCESSFUL_1 = _("Successful with warning, A transfer will take place once authorized by the receiver bank")
BANK_TRX_IS_SUCCESSFUL_2 = _("Successful, transaction is settled by the receiver bank")
INTERNAL_ERROR_MSG = _("Process stopped during an internal error, can you try again or contact your support team")
EXTERNAL_ERROR_MSG = _("Process stopped during an external error, can you try again or contact your support team")


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
    "ARIB",
    "PDAC",
    "NBG",
    "CBE",
    "BBE"
]

VALID_BANK_TRANSACTION_TYPES_LIST = [
    "CASH_TRANSFER",
    "SALARY",
    "PREPAID_CARD",
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

BANK_TRANSACTION_TYPES_DESCRIPTION_LIST = [
    {'type': _('salary')       , 'description': _('For concurrent or repeated payments')},
    {'type': _('credit_card')  , 'description': _('For credit cards payments')},
    {'type': _('prepaid_card') , 'description': _('For prepaid cards and Meeza cards payments')},
    {'type': _('cash_transfer'), 'description': _('For bank accounts, debit cards etc..')},
]

BANK_CODES = [
    {'name': _('Ahli United Bank')                              , 'code':  'AUB' },
    {'name': _('Citi Bank N.A. Egypt')                          , 'code':  'CITI'},
    {'name': _('MIDBANK')                                       , 'code':  'MIDB'},
    {'name': _('Banque Du Caire')                               , 'code':  'BDC' },
    {'name': _('HSBC Bank Egypt S.A.E')                         , 'code':  'HSBC'},
    {'name': _('Credit Agricole Egypt S.A.E')                   , 'code':  'CAE' },
    {'name': _('Egyptian Gulf Bank (EG-Bank)')                  , 'code':  'EGB' },
    {'name': _('The United Bank')                               , 'code':  'UB'  },
    {'name': _('Qatar National Bank Alahli')                    , 'code':  'QNB' },
    {'name': _('Arab Bank PLC')                                 , 'code':  'ARAB'},
    {'name': _('Emirates National Bank of Dubai')               , 'code':  'ENBD'},
    {'name': _('Al Ahli Bank of Kuwait – Egypt')                , 'code':  'ABK' },
    {'name': _('National Bank of Kuwait – Egypt')               , 'code':  'NBK' },
    {'name': _('Arab Banking Corporation - Egypt S.A.E (ABC)')  , 'code':  'ABC' },
    {'name': _('First Abu Dhabi Bank')                          , 'code':  'FAB' },
    {'name': _('Abu Dhabi Islamic Bank – Egypt')                , 'code':  'ADIB'},
    {'name': _('Commercial International Bank - Egypt S.A.E')   , 'code':  'CIB' },
    {'name': _('Housing And Development Bank')                  , 'code':  'HDB' },
    {'name': _('Banque Misr')                                   , 'code':  'MISR'},
    {'name': _('Arab African International Bank')               , 'code':  'AAIB'},
    {'name': _('Egyptian Arab Land Bank')                       , 'code':  'EALB'},
    {'name': _('Export Development Bank of Egypt')              , 'code':  'EDBE'},
    {'name': _('Faisal Islamic Bank of Egypt')                  , 'code':  'FAIB'},
    {'name': _('Blom Bank')                                     , 'code':  'BLOM'},
    {'name': _('Abu Dhabi Commercial Bank – Egypt')             , 'code':  'ADCB'},
    {'name': _('Alex Bank Egypt')                               , 'code':  'BOA' },
    {'name': _('Societe Arabe Internationale De Banque (SAIB)') , 'code':  'SAIB'},
    {'name': _('National Bank of Egypt')                        , 'code':  'NBE' },
    {'name': _('Al Baraka Bank Egypt B.S.C')                    , 'code':  'ABRK'},
    {'name': _('Egypt Post')                                    , 'code':  'POST'},
    {'name': _('Nasser Social Bank')                            , 'code':  'NSB' },
    {'name': _('Industrial Development Bank')                   , 'code':  'IDB' },
    {'name': _('Suez Canal Bank')                               , 'code':  'SCB' },
    {'name': _('Mashreq Bank')                                  , 'code':  'MASH'},
    {'name': _('Arab Investment Bank')                          , 'code':  'AIB' },
    {'name': _('Audi Bank')                                     , 'code':  'AUDI'},
    {'name': _('General Authority For Supply Commodities')      , 'code':  'GASC'},
    {'name': _('Arab International Bank')                       , 'code':  'ARIB'},
    {'name': _('Agricultural Bank of Egypt')                    , 'code':  'PDAC'},
    {'name': _('National Bank of Greece')                       , 'code':  'NBG' },
    {'name': _('Central Bank Of Egypt')                         , 'code':  'CBE' },
    {'name': _('Attijariwafa Bank')                             , 'code':  'BBE' }
  ]

ERROR_CODES_MESSAGES = {
    # Vodafone Cash Codes
    '403' : _('Channel Authentication Failed'),
    '404' : _('Undefined request type'),
    '406' : _('Incorrect input given to request'),
    '501' : _('Internal Error'),
    '583' : _('Exceeded Maximum Limit Per Single Transaction'),
    '604' : _('Below Minimum Transaction Limit Per Single Transaction'),
    '610' : _('User Not Eligible To Perform Transaction'),
    '615' : _('Sender and Recipient Accounts are the Same'),
    '618' : _('Recipient Is Unregistered'),
    '1051':	_('MSISDN Does Not Exist'),
    '1056':	_('Invalid Consumer PIN'),
    '1033':	_('Initial MPIN has not been changed'),
    '1069':	_('Sender and Recipient Accounts are the Same'),
    '1102':	_('M-PIN is Empty'),
    '1118':	_('MSISDN is Locked'),
    '1301':	_('Invalid Client ID'),
    '1996':	_('Catch All SE Errors'),
    '1997':	_('Inactive Service'),
    '4011':	_('Initial MPIN has not been changed.'),
    '4037':	_('Consumer MSISDN Does Not Exist'),
    '4051':	_('Agent MSISDN Does Not Exist'),
    '4055':	_('Consumer Account Status is Not Active'),
    '4056':	_('Invalid Agent M-PIN'),
    '4070':	_('Agent Type is Invalid'),
    '4081':	_('Consumer has No Default Funding Account'),
    '4139':	_('Agent MSISDN does not exist'),
    '4140':	_('Agent ID Does Not Exist'),
    '4333':	_("Recipient Consumer's MPIN has not been changed"),
    '4334':	_("Recipient Consumer's has exceeded transaction count limit"),
    '5465':	_('Service Call Failed'),
    '6001':	_('Funding Account Status is Referral'),
    '6003':	_('Invalid Agent'),
    '6004':	_('Funding Account Status is Pick-up CR Problem or Fraud/Capture Card'),
    '6005':	_('Funding Account was not Honored/General Decline'),
    '6012':	_('Invalid Transaction'),
    '6013':	_('Invalid Amount'),
    '6014':	_('Invalid Funding Account Card Number'),
    '6015':	_('Invalid Issuer'),
    '6030':	_('Format Error'),
    '6041':	_('Funding Account Status is Lost'),
    '6043':	_('Funding Account Status is Stolen'),
    '6051':	_('Funding Account has Insufficient Funds'),
    '6054':	_('Funding Account is Expired'),
    '6055':	_('Invalid C-PIN'),
    '6057':	_('Transaction Not Permitted to Issuer/Card Holder'),
    '6058':	_('Transaction Not Permitted to Acquirer/Terminal'),
    '6061':	_('Exceeded Transaction Amount Limit'),
    '6062':	_('Restricted Card'),
    '6063':	_('Security Violation'),
    '6065':	_('Exceeded Transaction Count Limit'),
    '6070':	_('Contact Card Issuer'),
    '6071':	_('C-PIN Not Changed'),
    '6075':	_('Allowable Number of C-PIN Tries Exceeded'),
    '6076':	_('Invalid/Non-Existent "To Account"'),
    '6077':	_('Invalid/Non-Existent "From Account"'),
    '6078':	_('Invalid/Non-Existent Account'),
    '6084':	_('Invalid Authorization Life Cycle'),
    '6086':	_('C-PIN Validation Not Possible'),
    '6088':	_('Cryptographic Failure'),
    '6089':	_('Unacceptable C-PIN'),
    '6091':	_('Authorization System/Issuer System Inoperative'),
    '6092':	_('Unable to Route Transaction'),
    '6094':	_('Duplicate Authorization Request'),
    '6096':	_('General System Error'),
    '6097':	_('MIP is Down/Not Connected'),
    '6098':	_('No Response from MIP'),
    '6099':	_('Catch All Acquirer SE Error'),

    # Etisalat Cash Codes
    '0'    : _('Successful transaction'),
    '90002': _('Invalid disbursement request'),
    '90003': _('Invalid or missing parameters'),
    '90007': _('Invalid or missing parameters'),
    '90005': _('Service is down'),
    '90006': _('Service is down'),
    '90093': _('Service temporarily suspended')
}

DEFAULT_LIST_PER_ADMIN_FOR_TRANSACTIONS_REPORT = [
    {
        'issuer': 'total',
        'total': 0,
        'count': 0,
        'fees': 0,
        'vat': 0
    },
    {
        'issuer': 'vodafone',
        'total': 0,
        'count': 0,
        'fees': 0,
        'vat': 0
    },
    {
        'issuer': 'etisalat',
        'total': 0,
        'count': 0,
        'fees': 0,
        'vat': 0
    },
    {
        'issuer': 'aman',
        'total': 0,
        'count': 0,
        'fees': 0,
        'vat': 0
    },
    {
        'issuer': 'orange',
        'total': 0,
        'count': 0,
        'fees': 0,
        'vat': 0
    },
    {
        'issuer': 'B',
        'total': 0,
        'count': 0,
        'fees': 0,
        'vat': 0
    },
    {
        'issuer': 'C',
        'total': 0,
        'count': 0,
        'fees': 0,
        'vat': 0
    }
]

DEFAULT_LIST_PER_ADMIN_FOR_TRANSACTIONS_REPORT_raseedy_vf = [
    {
        'issuer': 'total',
        'total': 0,
        'count': 0
    },
    {
        'issuer': 'vodafone',
        'total': 0,
        'count': 0
    },
    {
        'issuer': 'etisalat',
        'total': 0,
        'count': 0
    },
    {
        'issuer': 'aman',
        'total': 0,
        'count': 0
    },
    {
        'issuer': 'orange',
        'total': 0,
        'count': 0
    },
    {
        'issuer': 'B',
        'total': 0,
        'count': 0
    },
    {
        'issuer': 'C',
        'total': 0,
        'count': 0
    },
    {
        'issuer': 'default',
        'total': 0,
        'count': 0
    }
]

DEFAULT_PER_ADMIN_FOR_VF_FACILITATOR_TRANSACTIONS_REPORT = {
    'issuer': 'default',
    'total': 0,
    'count': 0,
}


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
    elif transaction_type.upper() == "PREPAID_CARD":
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


def determine_transaction_type(category_code, purpose):
    """Determine transaction type based on transaction category code and purpose"""
    if category_code == 'CASH' and purpose == 'SALA':
        return 'salary'
    elif category_code == 'PCRD' and purpose == 'CASH':
        return 'prepaid_card'
    elif category_code == 'CASH' and purpose == 'CCRD':
        return 'credit_card'
    else:
        return 'cash_transfer'


def get_error_description_from_error_code(code):
    """Map the error description for a specific error code"""
    if code and code in ERROR_CODES_MESSAGES.keys():
        return _(str(ERROR_CODES_MESSAGES.get(code)).capitalize())
    elif code and code == 'SUCCESS':
        return str(code).capitalize()

    return _('External error, please contact your support team for further details')


def add_fees_and_vat_to_qs(qs, admin, doc_obj):
    """Append fees and vat to the output transactions queryset values"""
    if not (admin.is_vodafone_default_onboarding or
            admin.is_vodafone_facilitator_onboarding or
            admin.is_banks_standard_model_onboaring):
        # handle fees and vat in case of qs is single step transactions
        if doc_obj == 'wallets':
            for trx in qs:
                trx.fees, trx.vat = Budget.objects.get(disburser=admin).calculate_fees_and_vat_for_amount(
                    trx.amount, trx.issuer_choice_verbose.lower()
                )
        elif doc_obj is None or doc_obj == 'bank-card' or doc_obj.is_bank_card:
            for trx in qs:
                trx.fees, trx.vat = Budget.objects.get(disburser=admin).calculate_fees_and_vat_for_amount(
                    trx.amount, 'C'
                )
        elif doc_obj.is_e_wallet:
            for trx in qs:
                trx.fees, trx.vat = Budget.objects.get(disburser=admin).calculate_fees_and_vat_for_amount(
                    trx.amount, trx.issuer
                )
        elif doc_obj.is_bank_wallet:
            for trx in qs:
                trx.fees, trx.vat = Budget.objects.get(disburser=admin).calculate_fees_and_vat_for_amount(
                    trx.amount, trx.issuer_type
                )
    return qs
