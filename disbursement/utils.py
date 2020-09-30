# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.utils.translation import gettext as _


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


def logging_message(logger, head, user, message):
    """
    Simple function that will take the logger and the message and log them in
    :param logger: the logger itself that will handle the log message
    :param head: the head/title of the log message
    :param user: the user being stored at the request
    :param message: the message that will be logged
    :return: The message will be logged into the specified logger
    """
    return logger.debug(_(f"{head}\nUser: {user}\n{message}"))


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
