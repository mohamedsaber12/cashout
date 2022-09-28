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
    "000012", "000013", "000014", "515", "001054",
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
    '6051':	_('Service temporarily suspended'),
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
    '90093': _('Service temporarily suspended'),
    '90040': _('عزيزي العميل أنت غير مشترك في خدمة اتصالات كاش، للاشتراك برجاء زيارة أقرب فرع من فروع اتصالات بالخط والرقم القومي للمزيد من المعلومات اتصل ب-778')
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

#################### payouts pakistan data #######################

WALLET_ISSUER_IMD = {
    "jazzcash": "585953",
    "easypaisa": "639390",
    "zong": "999919",
    "sadapay": "559049",
    "ubank": "581886",
    "bykea": "999921",
    "simpaisa": "999922",
    "tag": "999925",
    "opay": "999947",
}

BANK_NAME_IMD = {
    "habib metropolitan bank limited": "627408",
    "dubai islamic bank pakistan limited": "428273",
    "finca microfinance bank": "502841",
    "sindh bank": "505439",
    "mcb islamic banking": "507642",
    "citi bank": "508117",
    "apna microfinance bank": "581862",
    "nrsp microfinance bank ltd": "586010",
    "united bank": "588974",
    "mcb bank limited": "589388",
    "allied bank limited": "589430",
    "habib bank limited": "600648",
    "faysal bank limited": "601373",
    "askari commercial bank limited": "603011",
    "js bank": "603733",
    "summit bank": "604781",
    "samba bank": "606101",
    "icbc": "621464",
    "bank of punjab": "623977",
    "bank alfalah limited": "627100",
    "bank al habib limited": "627197",
    "standard chartered bank": "627271",
    "silk bank": "627544",
    "bank of khyber": "627618",
    "meezan bank limited": "627873",
    "first women bank limited": "628138",
    "central directorate of national savings (cdns)": "629116",
    "bank islami pakistan": "639357",
    "al baraka bank limited": "639530",
    "soneri bank limited": "786110",
    "national bank of pakistan": "958600",
    "abhi finance": "999926",
    "barwaqt": "999955",
}

VALID_BANK_NAMES_LIST = [
    "habib metropolitan bank limited",
    "dubai islamic bank pakistan limited",
    "finca microfinance bank",
    "sindh bank",
    "mcb islamic banking",
    "citi bank",
    "apna microfinance bank",
    "nrsp microfinance bank ltd",
    "united bank",
    "mcb bank limited",
    "allied bank limited",
    "habib bank limited",
    "faysal bank limited",
    "askari commercial bank limited",
    "js bank",
    "summit bank",
    "samba bank",
    "icbc",
    "bank of punjab",
    "bank alfalah limited",
    "bank al habib limited",
    "standard chartered bank",
    "silk bank",
    "bank of khyber",
    "meezan bank limited",
    "first women bank limited",
    "central directorate of national savings (cdns)",
    "bank islami pakistan",
    "al baraka bank limited",
    "soneri bank limited",
    "national bank of pakistan",
    "abhi finance",
    "barwaqt",
]

VALID_BANK_IMD_BIN_LIST = [
    "627408",
    "428273",
    "502841",
    "505439",
    "507642",
    "508117",
    "581862",
    "586010",
    "588974",
    "589388",
    "589430",
    "600648",
    "601373",
    "603011",
    "603733",
    "604781",
    "606101",
    "621464",
    "623977",
    "627100",
    "627197",
    "627271",
    "627544",
    "627618",
    "627873",
    "628138",
    "629116",
    "639357",
    "639530",
    "786110",
    "958600",
    "999926",
    "999955",
]

ONE_LINK_ERROR_CODES_MESSAGES = {
    "00": "PROCESSED OK",
    "01": "LIMIT EXCEEDED",
    "02": "INVALID ACCOUNT",
    "03": "ACCOUNT INACTIVE",
    "04": "LOW BALANCE",
    "05": "INVALID CARD",
    "06": "INVALID IMD",
    "07": "INVALID CARD DATA",
    "08": "INVALID CARD RECORD",
    "09": "FIELD ERROR",
    "10": "DUPLICATE TRANSACTION",
    "11": "BAD TRANSACTION CODE",
    "12": "INVALID CARD STATUS",
    "13": "INTERNAL DATABASE ERROR",
    "14": "WARM CARD",
    "15": "HOT CARD",
    "16": "BAD CARD STATUS",
    "17": "UNKNOWN AUTH MODE",
    "18": "INVALID TRANSACTION DATE",
    "19": "INVALID CURRENCY CODE",
    "20": "NO TRANSACTION ON IMD",
    "21": "NO TRANSACTION ON ACCT",
    "22": "BAD CARD CYCLE DAT E",
    "23": "BAD CARD CYCLE LENGTH",
    "24": "BAD PIN",
    "25": "CARD EXPIRED",
    "26": "INTERNAL ERROR",
    "27": "INTERNAL ERROR",
    "28": "NO ACCOUNTS LINKED",
    "29": "INTERNAL ERROR",
    "30": "ORIGINAL TRANSACTION NOT FOUND",
    "31": "INTERNAL ERROR",
    "32": "INTERNAL ERROR",
    "33": "INTERNAL ERROR",
    "34": "ORIGINAL NOT AUTHORIZED",
    "35": "ORIGINAL ALREADY REVERSED",
    "36": "ACQUIRER REVERSAL",
    "37": "INVALID REPLACEMENT AMOUNT",
    "38": "TRANSACTION CODE MISMATCH",
    "39": "BAD TRANSACTION TYPE",
    "40": "INTERNAL ERROR",
    "41": "EXPIRY DATE MISMATCH",
    "42": "ACQUIRER ADJUSTMENT",
    "43": "ACQUIRER NACK",
    "44": "ORIGINAL ALREADY NACKED",
    "45": "T2 DATA MISMATCH",
    "46": "UNABLE TO PROCESS",
    "47": "ERR CURRENCY CONVERSION",
    "48": "BAD AMOUNT",
    "49": "INTERNAL ERROR",
    "50": "HOST STATUS UNKNOWN",
    "51": "HOST NOT PROCESSING",
    "52": "HOST IN STANDIN MODE",
    "53": "HOST IN BAL DWNLD MODE",
    "54": "SAF TRANSMIT MODE",
    "55": "HOST LINK DOWN",
    "56": "SENT TO HOST",
    "57": "INTERNAL ERROR",
    "58": "TRANSACTION TIMEDOUT",
    "59": "HOST REJECT",
    "60": "PIN RETRIES EXHAUSTED",
    "61": "TRANSACTION REJECTED, PLEASE SWITCH TO CONTACT INTERFACE",
    "62": "TRANSACTION REJECTED, PERFORM TRANSACTION AGAIN WITH CARDHOLDER AUTHENTICATION REQUIRED",
    "63": "DESTINATION NOT FOUND",
    "64": "DESTINATION NOT REGISTERED",
    "65": "CASH TRANSACTION NOT ALLOWED",
    "66": "NO TRANSACTION ALLOWED",
    "67": "INVALID ACCOUNT STATUS",
    "68": "INVALID TO ACCOUNT",
    "69": "BAD PIN COMPARE",
    "70": "REFUSED IMD",
    "71": "NO PROFILE AVAILABLE",
    "72": "CURRENCY NOT ALLOWED",
    "73": "CHECK DIGIT FAILED",
    "74": "TRANSACTION SOURCE NOT ALLOWED",
    "75": "UNKNOWN TRANSACTION SOURCE",
    "76": "MANUAL ENTRY NOT ALLOWED",
    "77": "REFER TO ISSUER",
    "78": "INVALID MERCHANT",
    "79": "HONOR WITH ID",
    "80": "MESSAGE FORMAT ERROR",
    "81": "SECURITY VIOLATION",
    "82": "MAIL ORDER NOT ALLOWED",
    "83": "NO COMMS KEY",
    "84": "NO PIN KEY",
    "85": "NO DEC TAB",
    "86": "INCORRECT PIN LEN",
    "87": "CASH RETRACT",
    "88": "FAULTY DISPENSE",
    "89": "SHORT DISPENSE",
    "90": "CUSTOMER NOT FOUND",
    "91": "ISSUER REVERSAL",
    "92": "ACCOUNT LOCKED",
    "93": "CUSTOMER RELATION NOT FOUND",
    "94": "PERMISSION DENIED",
    "95": "TRANSACTION REJECTED",
    "96": "ORIGINAL ALREADY REJECTED",
    "97": "BAD EXP DATE",
    "98": "ORIGINAL AMOUNT INCORRECT",
    "99": "ORIGINAL DATA ELEMENT MISMATCH",
    "424": EXTERNAL_ERROR_MSG,
}
