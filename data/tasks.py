# -*- coding: UTF-8 -*-
from __future__ import print_function

import csv
import json
import logging
import re
from decimal import Decimal

import pandas as pd
import requests
import tablib
import xlrd
import xlwt
from celery import Task
from dateutil.parser import parse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Case, Count, F, Q, Sum, When
from django.urls import reverse
from django.utils.timezone import datetime, make_aware
from django.utils.translation import gettext as _

from core.models import AbstractBaseStatus
from core.utils.validations import phonenumber_form_validate
from disbursement.models import BankTransaction, DisbursementData
from disbursement.resources import (DisbursementDataResourceForBankCards,
                                    DisbursementDataResourceForBankWallet,
                                    DisbursementDataResourceForEWallets)
from disbursement.utils import (DEFAULT_LIST_PER_ADMIN_FOR_TRANSACTIONS_REPORT,
                                DEFAULT_PER_ADMIN_FOR_VF_FACILITATOR_TRANSACTIONS_REPORT,
                                VALID_BANK_CODES_LIST,
                                VALID_BANK_TRANSACTION_TYPES_LIST,
                                determine_trx_category_and_purpose)
from instant_cashin.models import AbstractBaseIssuer, InstantTransaction
from instant_cashin.utils import get_digits, get_from_env
from payouts.settings.celery import app
from users.models import CheckerUser, Levels, UploaderUser, User
from utilities.functions import get_value_from_env
from utilities.messages import MSG_TRY_OR_CONTACT, MSG_WRONG_FILE_FORMAT
from utilities.models import Budget

from .decorators import respects_language
from .models import Doc, FileData
from .utils import deliver_mail, export_excel, randomword

CHANGE_PROFILE_LOGGER = logging.getLogger("change_fees_profile")
CHECKERS_NOTIFICATION_LOGGER = logging.getLogger("checkers_notification")

MSG_NOT_WITHIN_THRESHOLD = _(f"File's total amount exceeds your current balance, please contact your support team")
MSG_MAXIMUM_ALLOWED_AMOUNT_TO_BE_DISBURSED = _(f"File's total amount exceeds your maximum amount that can be disbursed,"
                                               f" please contact your support team")
MSG_REGISTRATION_PROCESS_ERROR = _(f"Registration process stopped during an internal error, {MSG_TRY_OR_CONTACT}")
MSG_CHANGE_PROFILE_ERROR = _(f"Internal error while trying to apply the fees, {MSG_TRY_OR_CONTACT}")


UPLOAD_LOGGER = logging.getLogger("upload")


class BankWalletsAndCardsSheetProcessor(Task):
    """
    Task to process and validate bank wallets uploaded sheets.
    https://medium.com/casual-inference/the-most-time-efficient-ways-to-import-csv-data-in-python-cc159b44063d
    """

    def amount_is_valid_digit(self, amount):
        return str(amount).replace('.', '', 1).isdigit()

    def determine_max_amount_can_be_disbursed(self, doc_obj):
        """
        :param doc_obj: document to be processed
        :return: max_amount_can_be_disbursed
        """
        return max([level.max_amount_can_be_disbursed for level in Levels.objects.filter(created=doc_obj.owner.root)])

    def determine_csv_delimiter(self, doc_obj):
        """
        :param doc_obj: csv document to be processed
        :return: the delimiter used at the csv sheet or False if there is any problem
        """
        try:
            as_string = doc_obj.file.read().decode("utf-8")
            dialect = csv.Sniffer().sniff(as_string)
            doc_obj.file.seek(0)
            return dialect.delimiter
        except:
            return False

    def accumulate_df(self, doc_obj):
        """
        :param doc_obj: document to be processed
        :return: data frame using pandas package
        """
        doc_type = "csv" if doc_obj.file.name.endswith(".csv") else "excel"

        if doc_type == "excel":
            df = pd.read_excel(doc_obj.file)
        else:
            df = pd.read_csv(doc_obj.file, delimiter=self.determine_csv_delimiter(doc_obj))

        return df

    def end_with_failure(self, doc_obj, failure_message):
        """
        :param doc_obj: document to be processed
        :param failure_message: the processing failure message to be recorded
        :return: data frame using pandas package
        """
        doc_obj.processing_failure(failure_message)
        notify_maker(doc_obj)
        file_type = "wallets file" if doc_obj.is_bank_wallet else "cards file"
        UPLOAD_LOGGER.debug(f"[message] [bank {file_type} processing error] [celery_task] -- {failure_message}")

    def end_with_failure_sheet_details(self,
                                       doc_obj,
                                       numbers_list,
                                       amount_list,
                                       names_list,
                                       issuers_list=None,
                                       codes_list=None,
                                       purposes_list=None,
                                       errors_list=None):
        if doc_obj.is_bank_wallet:
            sheet_data = list(zip(numbers_list, amount_list, names_list, issuers_list, errors_list))
            headers = ["mobile number", "amount", "full name", "issuer", "errors"]
        else:
            sheet_data = list(zip(numbers_list, amount_list, names_list, codes_list, purposes_list, errors_list))
            headers = ["account number", "amount", "full name", "bank swift code", "transaction type", "errors"]

        filename = f"failed_validations_{randomword(4)}.xlsx"
        file_path = f"{settings.MEDIA_ROOT}/documents/disbursement/{filename}"
        error_message = _("File validation error")
        sheet_data.insert(0, headers)
        export_excel(file_path, sheet_data)
        download_url = settings.BASE_URL + \
                       str(reverse('disbursement:download_validation_failed', kwargs={'doc_id': doc_obj.id})) + \
                       f"?filename={filename}"
        doc_obj.processing_failure(error_message)
        notify_maker(doc_obj, download_url)

    def process_and_validate_wallets_records(self, df):
        """
        :param df: data frame read from the uploaded document
        :return: msisdn_list, amount_list, names_list, errors_list, total_amount
        """
        total_amount = 0
        msisdns_list, amounts_list, names_list, issuers_list, errors_list = [], [], [], [], []

        try:
            for record in df.itertuples():
                index = record[0]
                errors_list.append(None)

                # 1. Validate msisdns
                msisdn = str(record[1])
                valid_msisdn = False
                try:
                    if msisdn.startswith("1") and len(msisdn) == 10:
                        phonenumber_form_validate(f"+20{msisdn}")
                        msisdn = f"0020{msisdn}"
                        msisdns_list.append(msisdn)
                        valid_msisdn = True
                    elif msisdn.startswith("01") and len(msisdn) == 11:
                        phonenumber_form_validate(f"+2{msisdn}")
                        msisdn = f"002{msisdn}"
                        msisdns_list.append(msisdn)
                        valid_msisdn = True
                    elif msisdn.startswith("2") and len(msisdn) == 12:
                        phonenumber_form_validate(f"+{msisdn}")
                        msisdn = f"00{msisdn}"
                        msisdns_list.append(msisdn)
                        valid_msisdn = True
                except ValidationError:
                    if errors_list[index]:
                        errors_list[index] = "Invalid mobile number"
                    else:
                        errors_list[index] = "\nInvalid mobile number"
                    msisdns_list.append(msisdn)

                if valid_msisdn and len(list(filter(lambda ms: ms == msisdn, msisdns_list))) > 1:
                    if errors_list[index]:
                        errors_list[index] = "Duplicate mobile number"
                    else:
                        errors_list[index] = "\nDuplicate mobile number"

                # 2. Validate amounts
                if self.amount_is_valid_digit(record[2]) and float(record[2]) >= 1.0:
                    amounts_list.append(round(Decimal(record[2]), 2))
                    total_amount += round(Decimal(record[2]), 2)
                else:
                    if errors_list[index]:
                        errors_list[index] = "Invalid amount"
                    else:
                        errors_list[index] = "\nInvalid amount"
                    amounts_list.append(record[2])

                # 3. Validate for empty names
                names_list.append(record[3])
                if not record[3]:
                    if errors_list[index]:
                        errors_list[index] = "Invalid name"
                    else:
                        errors_list[index] = "\nInvalid name"

                # 4. Validate issuer
                issuer = str(record[4])
                issuers_list.append(issuer)
                if not issuer or issuer.lower() not in ["orange", "bank_wallet"]:
                    if errors_list[index]:
                        errors_list[index] = "Invalid issuer option"
                    else:
                        errors_list[index] = "\nInvalid issuer option"

        except Exception as e:
            raise Exception(e)
        return msisdns_list, amounts_list, names_list, issuers_list, errors_list, total_amount

    def process_and_validate_cards_records(self, df):
        """
        :param df: data frame read from the uploaded document
        :return: msisdn_list, amount_list, names_list, codes_list, purposes_list, errors_list, total_amount
        """
        total_amount = 0
        accounts_list, amount_list, names_list, codes_list, purposes_list, errors_list = [], [], [], [], [], []

        try:
            for record in df.itertuples():
                index = record[0]
                errors_list.append(None)

                # 1.1 Validate account numbers
                account = get_digits(str(record[1]))
                valid_account = False
                if account and (6 <= len(account) <= 20):
                    accounts_list.append(account)
                    valid_account = True
                # check account is iban number
                elif str(record[1]).startswith('EG') and account and len(account) == 27:
                    accounts_list.append(str(record[1]))
                    valid_account = True
                else:
                    if errors_list[index]:
                        errors_list[index] = "Invalid account number"
                    else:
                        errors_list[index] = "\nInvalid account number"
                    accounts_list.append(account)

                # 1.2 Validate for duplicate account numbers
                if valid_account and len(list(filter(lambda acc: acc == account, accounts_list))) > 1:
                    if errors_list[index]:
                        errors_list[index] = "Duplicate account number"
                    else:
                        errors_list[index] = "\nDuplicate account number"
                        accounts_list.append(record[1])

                # 2. Validate amounts
                if self.amount_is_valid_digit(record[2]) and float(record[2]) >= 1.0:
                    amount_list.append(round(Decimal(record[2]), 2))
                    total_amount += round(Decimal(record[2]), 2)
                else:
                    if errors_list[index]:
                        errors_list[index] = "Invalid amount"
                    else:
                        errors_list[index] = "\nInvalid amount"
                    amount_list.append(record[2])

                # 3. Validate for empty names
                names_list.append(record[3])
                if not record[3]:
                    if errors_list[index]:
                        errors_list[index] = "Invalid name"
                    else:
                        errors_list[index] = "\nInvalid name"

                # 4. Validate banks swift codes
                codes_list.append(record[4])
                if not record[4] or str(record[4]).upper() not in VALID_BANK_CODES_LIST:
                    if errors_list[index]:
                        errors_list[index] = "Invalid bank swift code"
                    else:
                        errors_list[index] = "\nInvalid bank swift code"

                # 5. Validate transaction purpose
                purposes_list.append(record[5])
                if not record[5] or str(record[5]).upper() not in VALID_BANK_TRANSACTION_TYPES_LIST:
                    if errors_list[index]:
                        errors_list[index] = "Invalid transaction purpose"
                    else:
                        errors_list[index] = "\nInvalid transaction purpose"
        except:
            pass
        finally:
            return accounts_list, amount_list, names_list, codes_list, purposes_list, errors_list, total_amount

    def save_processed_records_to_db(self,
                                     doc_obj,
                                     amounts_list,
                                     names_list,
                                     recipients_list,
                                     issuers_list=None,
                                     codes_list=None,
                                     purposes_list=None):
        """"""

        # 1 For bank wallets/Orange: Save the refined data as instant transactions records
        if doc_obj.is_bank_wallet:
            processed_data = zip(amounts_list, names_list, recipients_list, issuers_list)
            objs = [
                InstantTransaction(
                        document=doc_obj,
                        issuer_type=AbstractBaseIssuer.ORANGE if record[3].lower() == "orange"
                                                                                    else AbstractBaseIssuer.BANK_WALLET,
                        amount=record[0],
                        recipient_name=record[1],
                        anon_recipient=record[2]
                ) for record in processed_data
            ]
            InstantTransaction.objects.bulk_create(objs=objs)

        # 2 For bank cards: Save the refined data as bank transactions records
        elif doc_obj.is_bank_card:
            processed_data = zip(amounts_list, names_list, recipients_list, codes_list, purposes_list)
            for record in processed_data:
                category_purpose_dict = determine_trx_category_and_purpose(record[4])
                BankTransaction.objects.create(
                        currency="EGP",
                        debtor_address_1="EG",
                        creditor_address_1="EG",
                        corporate_code=get_from_env("ACH_CORPORATE_CODE"),
                        debtor_account=get_from_env("ACH_DEBTOR_ACCOUNT"),
                        document=doc_obj,
                        user_created=doc_obj.owner,
                        amount=record[0],
                        creditor_name=record[1],
                        creditor_account_number=record[2],
                        creditor_bank=record[3],
                        category_code=category_purpose_dict.get("category_code", "CASH"),
                        purpose=category_purpose_dict.get("purpose", "CASH")
                )

    def run(self, doc_id, *args, **kwargs):
        """
        :param doc_id: id of the document being disbursed
        :return
        """
        try:
            doc_obj = Doc.objects.get(id=doc_id)
            budget_fees_key = "bank_card" if doc_obj.is_bank_card else "bank_wallet"
            file_type = "wallets file" if doc_obj.is_bank_wallet else "cards file"
            callwallets_moderator = doc_obj.owner.root.callwallets_moderator.first()
            max_amount_can_be_disbursed = self.determine_max_amount_can_be_disbursed(doc_obj)
            df = self.accumulate_df(doc_obj)
            rows_count = df.count()

            # 1.1 For bank wallets: Check if all records has no empty values
            if doc_obj.is_bank_wallet:
                if not (rows_count["mobile number"] == rows_count["amount"] ==
                        rows_count["full name"] == rows_count["issuer"]):
                    self.end_with_failure(doc_obj, MSG_WRONG_FILE_FORMAT)
                    return False
                msisdn_list, amounts_list, names_list, issuers_list, errors_list, total_amount = \
                    self.process_and_validate_wallets_records(df)

            # 1.2 For bank cards: Check if all records has no empty values
            elif doc_obj.is_bank_card:
                if not (rows_count["account number"] == rows_count["amount"] ==
                        rows_count["full name"] == rows_count["bank swift code"] == rows_count["transaction type"]):
                    self.end_with_failure(doc_obj, MSG_WRONG_FILE_FORMAT)
                    return False
                accounts_list, amounts_list, names_list, codes_list, purposes_list, errors_list, total_amount = \
                    self.process_and_validate_cards_records(df)

            doc_obj.total_amount = total_amount
            doc_obj.total_count = max(rows_count)

            # 2. Check if the entity admin is privileged to disburse sheets
            if not callwallets_moderator.disbursement:
                self.end_with_failure(doc_obj, f"Your entity is suspended from disbursing sheets, {MSG_TRY_OR_CONTACT}")
                return False

            # 3. Check if there is any errors happened at sheet processing
            elif len([value for value in errors_list if value]) > 0:
                if doc_obj.is_bank_wallet:
                    self.end_with_failure_sheet_details(
                            doc_obj, msisdn_list, amounts_list, names_list, issuers_list=issuers_list,
                            errors_list=errors_list
                    )
                elif doc_obj.is_bank_card:
                    self.end_with_failure_sheet_details(
                            doc_obj, accounts_list, amounts_list, names_list, codes_list=codes_list,
                            purposes_list=purposes_list, errors_list=errors_list
                    )
                return False

            # 4. Check if the sheet's total amount doesn't exceed maximum amount that can be disbursed for this checker
            elif total_amount > max_amount_can_be_disbursed:
                self.end_with_failure(doc_obj, MSG_MAXIMUM_ALLOWED_AMOUNT_TO_BE_DISBURSED)
                return False

            # 5. Check if the sheet's total amount doesn't exceed the current available budget of the entity
            elif not Budget.objects.get(disburser=doc_obj.owner.root).within_threshold(total_amount, budget_fees_key):
                self.end_with_failure(doc_obj, MSG_NOT_WITHIN_THRESHOLD)
                return False

            # 6.1 For bank wallets/Orange: Save the refined data as instant transactions records
            if doc_obj.is_bank_wallet:
                self.save_processed_records_to_db(doc_obj, amounts_list, names_list, msisdn_list, issuers_list)

            # 6.2 For bank cards: Save the refined data as bank transactions records
            elif doc_obj.is_bank_card:
                self.save_processed_records_to_db(
                        doc_obj, amounts_list, names_list, accounts_list, codes_list=codes_list,
                        purposes_list=purposes_list
                )

            # 7. Change doc status to processed successfully and notify makers that doc passed validations
            doc_obj.has_change_profile_callback = True
            doc_obj.processed_successfully()
            notify_maker(doc_obj)
            UPLOAD_LOGGER.debug(f"[message] [bank {file_type} passed processing] [celery_task] -- Doc id: {doc_id}")
            return True
        except Doc.DoesNotExist:
            UPLOAD_LOGGER.debug(f"[message] [bank file processing error] [celery_task] -- Doc id: {doc_id} not found")
            return False
        except Exception as err:
            self.end_with_failure(doc_obj, MSG_REGISTRATION_PROCESS_ERROR)
            UPLOAD_LOGGER.debug(f"[message] [bank {file_type} processing error] [celery_task] -- {err.args}")
            return False


class EWalletsSheetProcessor(Task):
    """
    Task to process and validate vodafone/etisalat/aman uploaded sheets.
    """

    doc_obj = None
    is_normal_sheet_specs = None

    def amount_is_valid_digit(self, amount):
        return str(amount).replace('.', '', 1).isdigit()

    def return_total_amount_plus_fees_regarding_specific_issuer(self, amount_list, issuer, amount_list_length):
        return Budget.objects.get(disburser=self.doc_obj.owner.root).\
            accumulate_amount_with_fees_and_vat(sum(amount_list), issuer, amount_list_length)

    def determine_max_amount_can_be_disbursed(self):
        """:return: max_amount_can_be_disbursed"""
        # TODO: Move this query to a separate queryset at Level model custom manager
        return max(
                [level.max_amount_can_be_disbursed for level in Levels.objects.filter(created=self.doc_obj.owner.root)]
        )

    def determine_csv_delimiter(self):
        """:return: the delimiter used at the csv sheet or False if there is any problem"""
        try:
            as_string = self.doc_obj.file.read().decode("utf-8")
            dialect = csv.Sniffer().sniff(as_string)
            self.doc_obj.file.seek(0)
            return dialect.delimiter
        except:
            return False

    def accumulate_df(self):
        """:return: data frame using pandas package"""
        doc_type = "csv" if self.doc_obj.file.name.endswith(".csv") else "excel"

        if doc_type == "excel":
            df = pd.read_excel(self.doc_obj.file)
        else:
            df = pd.read_csv(self.doc_obj.file, delimiter=self.determine_csv_delimiter())

        return df

    def determine_headers_names(self, df):
        amount_position, msisdn_position, issuer_position = self.doc_obj.file_category.fields_cols()
        msisdn_header = df.columns[msisdn_position]
        amount_header = df.columns[amount_position]
        issuer_header = df.columns[issuer_position] if issuer_position else False

        return msisdn_header, amount_header, issuer_header

    def determine_starting_index(self):
        return self.doc_obj.file_category.starting_row()

    def end_with_failure(self, failure_message):
        """
        :param failure_message: the processing failure message to be recorded
        :return: data frame using pandas package
        """
        self.doc_obj.processing_failure(failure_message)
        notify_maker(self.doc_obj)
        UPLOAD_LOGGER.debug(f"[message] [ewallets file processing error] [celery_task] -- {failure_message}")

    def end_with_failure_sheet_details(self, numbers_list, amount_list, issuers_list=None, errors_list=None):
        if self.is_normal_sheet_specs:
            sheet_data = list(zip(numbers_list, amount_list, errors_list))
            headers = ["mobile number", "amount", "errors"]
        else:
            sheet_data = list(zip(numbers_list, amount_list, issuers_list, errors_list))
            headers = ["mobile number", "amount", "issuer", "errors"]

        filename = f"failed_validations_{randomword(4)}.xlsx"
        file_path = f"{settings.MEDIA_ROOT}/documents/disbursement/{filename}"
        error_message = _("Validation error, file with errors sent to the maker user.")
        sheet_data.insert(0, headers)
        export_excel(file_path, sheet_data)
        download_url = settings.BASE_URL + \
                       str(reverse('disbursement:download_validation_failed', kwargs={'doc_id': self.doc_obj.id})) + \
                       f"?filename={filename}"
        self.doc_obj.processing_failure(error_message)
        notify_maker(self.doc_obj, download_url)

    def process_and_validate_normal_specs_records(self, df, msisdn_header, amount_header):
        """
        :param df: data frame read from the uploaded document
        :return: msisdn_list, amount_list, errors_list, total_amount
        """
        total_amount = 0
        msisdns_list, amounts_list, errors_list = [], [], []

        try:
            for index, record in df.iterrows():
                errors_list.append(None)

                # 1. Validate msisdns
                msisdn = str(record[msisdn_header])
                valid_msisdn = False
                try:
                    if msisdn.startswith("1") and len(msisdn) == 10:
                        phonenumber_form_validate(f"+20{msisdn}")
                        msisdn = f"0020{msisdn}"
                        msisdns_list.append(msisdn)
                        valid_msisdn = True
                    elif msisdn.startswith("01") and len(msisdn) == 11:
                        phonenumber_form_validate(f"+2{msisdn}")
                        msisdn = f"002{msisdn}"
                        msisdns_list.append(msisdn)
                        valid_msisdn = True
                    elif msisdn.startswith("2") and len(msisdn) == 12:
                        phonenumber_form_validate(f"+{msisdn}")
                        msisdn = f"00{msisdn}"
                        msisdns_list.append(msisdn)
                        valid_msisdn = True
                    else:
                        raise ValidationError('')
                except ValidationError:
                    if errors_list[index]:
                        errors_list[index] = "Invalid mobile number"
                    else:
                        errors_list[index] = "\nInvalid mobile number"
                    msisdns_list.append(msisdn)

                if valid_msisdn and len(list(filter(lambda ms: ms == msisdn, msisdns_list))) > 1:
                    if errors_list[index]:
                        errors_list[index] = "Duplicate mobile number"
                    else:
                        errors_list[index] = "\nDuplicate mobile number"

                # 2. Validate amounts
                if self.amount_is_valid_digit(str(record[amount_header])) and float(str(record[amount_header])) >= 1.0:
                    amounts_list.append(round(Decimal(str(record[amount_header])), 2))
                    total_amount += round(Decimal(str(record[amount_header])), 2)
                else:
                    if errors_list[index]:
                        errors_list[index] = "Invalid amount"
                    else:
                        errors_list[index] = "\nInvalid amount"
                    amounts_list.append(record[amount_header])

        except Exception as e:
            raise Exception(e)
        return msisdns_list, amounts_list, errors_list, total_amount, msisdns_list

    def process_and_validate_issuers_specs_records(self, df, msisdn_header, amount_header, issuer_header):
        """
        :param df: data frame read from the uploaded document
        :return: msisdn_list, amount_list, issuers_list, errors_list, total_amount
        """
        total_amount = 0
        valid_issuers_list = ['vodafone', 'etisalat', 'aman']
        msisdns_list, amounts_list, issuers_list, errors_list, vf_msisdns_list = [], [], [], [], []

        try:
            for index, record in df.iterrows():
                errors_list.append(None)

                # 1. Validate msisdns
                msisdn = str(record[msisdn_header])
                valid_msisdn = False
                try:
                    if msisdn.startswith("1") and len(msisdn) == 10:
                        phonenumber_form_validate(f"+20{msisdn}")
                        msisdn = f"0020{msisdn}"
                        msisdns_list.append(msisdn)
                        valid_msisdn = True
                    elif msisdn.startswith("01") and len(msisdn) == 11:
                        phonenumber_form_validate(f"+2{msisdn}")
                        msisdn = f"002{msisdn}"
                        msisdns_list.append(msisdn)
                        valid_msisdn = True
                    elif msisdn.startswith("2") and len(msisdn) == 12:
                        phonenumber_form_validate(f"+{msisdn}")
                        msisdn = f"00{msisdn}"
                        msisdns_list.append(msisdn)
                        valid_msisdn = True
                except ValidationError:
                    if errors_list[index]:
                        errors_list[index] = "Invalid mobile number"
                    else:
                        errors_list[index] = "\nInvalid mobile number"
                    msisdns_list.append(msisdn)

                if valid_msisdn and len(list(filter(lambda ms: ms == msisdn, msisdns_list))) > 1:
                    if errors_list[index]:
                        errors_list[index] = "Duplicate mobile number"
                    else:
                        errors_list[index] = "\nDuplicate mobile number"

                # 2. Validate amounts
                if self.amount_is_valid_digit(str(record[amount_header])) and float(str(record[amount_header])) >= 1.0:
                    amounts_list.append(round(Decimal(str(record[amount_header])), 2))
                    total_amount += round(Decimal(str(record[amount_header])), 2)
                else:
                    if errors_list[index]:
                        errors_list[index] = "Invalid amount"
                    else:
                        errors_list[index] = "\nInvalid amount"
                    amounts_list.append(str(record[amount_header]))

                # 3. Validate issuer
                issuer = str(record[issuer_header]).lower().strip()
                issuers_list.append(issuer)
                if issuer not in valid_issuers_list:
                    if errors_list[index]:
                        errors_list[index] = "Invalid issuer option"
                    else:
                        errors_list[index] = "\nInvalid issuer option"

                # 4. Accumulate vodafone msisdns list
                if issuer == "vodafone":
                    vf_msisdns_list.append(msisdn)

        except Exception as e:
            raise Exception(e)
        return msisdns_list, amounts_list, issuers_list, errors_list, total_amount, vf_msisdns_list

    def validate_doc_total_amount_against_custom_budget(self, issuers_list, amounts_list):
        vf_amount_list, ets_amount_list, aman_amount_list = [], [], []
        vf_total_amount = ets_total_amount = aman_total_amount = 0
        current_custom_budget = Budget.objects.get(disburser=self.doc_obj.owner.root).current_balance

        if self.doc_obj.owner.is_accept_vodafone_onboarding:
            for issuer, amount in zip(issuers_list, amounts_list):
                if issuer == "vodafone":
                    vf_amount_list.append(amount)
                elif issuer == "etisalat":
                    ets_amount_list.append(amount)
                elif issuer == "aman":
                    aman_amount_list.append(amount)
        else:
            vf_amount_list = amounts_list

        if vf_amount_list:
            vf_total_amount = self.return_total_amount_plus_fees_regarding_specific_issuer(vf_amount_list, "vodafone", len(vf_amount_list))
        if ets_amount_list:
            ets_total_amount = self.return_total_amount_plus_fees_regarding_specific_issuer(ets_amount_list, "etisalat", len(ets_amount_list))
        if aman_amount_list:
            aman_total_amount = self.return_total_amount_plus_fees_regarding_specific_issuer(aman_amount_list, "aman", len(aman_amount_list))

        self.doc_obj.total_amount_with_fees_vat = sum([vf_total_amount, ets_total_amount, aman_total_amount])
        return self.doc_obj.total_amount_with_fees_vat <= current_custom_budget

    def change_profile_for_vodafone_recipients(self, vodafone_recipients_list):
        """
        Change fees profile for vodafone recipients.
        :return: True or False
        """
        superadmin = self.doc_obj.owner.root.client.creator
        wallets_env_url = get_value_from_env(superadmin.vmt.vmt_environment)
        response_has_error = True
        if self.doc_obj.owner.is_vodafone_default_onboarding or \
            self.doc_obj.owner.is_banks_standard_model_onboaring:
            fees_profile = self.doc_obj.owner.root.client.get_fees()
        else:
            fees_profile = self.doc_obj.owner.root.super_admin.wallet_fees_profile
        payload = superadmin.vmt.accumulate_change_profile_payload(vodafone_recipients_list, fees_profile)

        try:
            CHANGE_PROFILE_LOGGER.debug(f"[request] [change fees profile] [{self.doc_obj.owner}] -- {payload}")
            response = requests.post(wallets_env_url, json=payload, verify=False)
        except Exception as e:
            CHANGE_PROFILE_LOGGER.debug(f"[message] [change fees profile error] [{self.doc_obj.owner}] -- {e.args}")
            self.end_with_failure(_(MSG_CHANGE_PROFILE_ERROR))
            return False

        CHANGE_PROFILE_LOGGER.debug(f"[response] [change fees profile] [{self.doc_obj.owner}] -- {str(response.text)}")
        if response.ok:
            response_dict = response.json()
            if response_dict["TXNSTATUS"] == "200":
                self.doc_obj.txn_id = response_dict["BATCH_ID"]
                response_has_error = False
            else:
                response_has_error = response_dict.get("MESSAGE") or _(CHANGE_PROFILE_LOGGER)

        if response_has_error:
            self.end_with_failure(_(MSG_CHANGE_PROFILE_ERROR))
            return False

        return True

    def run(self, doc_id, *args, **kwargs):
        try:
            self.doc_obj = Doc.objects.get(id=doc_id)
            self.is_normal_sheet_specs = self.doc_obj.owner.root.root_entity_setups.is_normal_flow
            wallets_moderator = self.doc_obj.owner.root.callwallets_moderator.first()
            max_amount_can_be_disbursed = self.determine_max_amount_can_be_disbursed()
            df = self.accumulate_df()
            rows_count = df.count()
            msisdn_header, amount_header, issuer_header = self.determine_headers_names(df)
            start_row = self.determine_starting_index()
            issuers_list = None

            # 1.1 For normal sheet specs: Check if all records has no empty values
            if self.is_normal_sheet_specs:
                if not (rows_count[msisdn_header] == rows_count[amount_header]):
                    self.end_with_failure(MSG_WRONG_FILE_FORMAT)
                    return False
                msisdn_list, amounts_list, errors_list, total_amount, vf_msisdns_list = \
                    self.process_and_validate_normal_specs_records(df, msisdn_header, amount_header)

            # 1.2 For issuer based sheet specs: Check if all records has no empty values
            else:
                if not (rows_count[msisdn_header] == rows_count[amount_header] == rows_count[issuer_header]):
                    self.end_with_failure(MSG_WRONG_FILE_FORMAT)
                    return False
                msisdn_list, amounts_list, issuers_list, errors_list, total_amount, vf_msisdns_list = \
                    self.process_and_validate_issuers_specs_records(df, msisdn_header, amount_header, issuer_header)

            self.doc_obj.total_amount = total_amount
            self.doc_obj.total_count = max(rows_count)

            # 2. Check if the entity admin is privileged to disburse sheets
            if not wallets_moderator.disbursement:
                self.end_with_failure(f"Your entity is suspended from disbursing sheets, {MSG_TRY_OR_CONTACT}")
                return False

            # 3. Check if there is any errors happened at sheet processing
            elif len([value for value in errors_list if value]) > 0:
                if self.is_normal_sheet_specs:
                    self.end_with_failure_sheet_details(msisdn_list, amounts_list, errors_list=errors_list)
                else:
                    self.end_with_failure_sheet_details(
                            msisdn_list, amounts_list, issuers_list, errors_list=errors_list
                    )
                return False

            # 4. Check if the sheet's total amount doesn't exceed maximum amount that can be disbursed for this checker
            elif total_amount > max_amount_can_be_disbursed:
                self.end_with_failure(MSG_MAXIMUM_ALLOWED_AMOUNT_TO_BE_DISBURSED)
                return False
            

            # 5. Validate doc total amount against custom budget for paymob send model and vodafone facilitator model
            elif not self.doc_obj.owner.is_vodafone_default_onboarding\
                and not self.doc_obj.owner.is_banks_standard_model_onboaring:
                has_sufficient_budget = self.validate_doc_total_amount_against_custom_budget(issuers_list, amounts_list)
                if not has_sufficient_budget:
                    self.end_with_failure(MSG_NOT_WITHIN_THRESHOLD)
                    return False

            # 6. Make change fees profile request for vodafone recipients only
            if wallets_moderator.change_profile and vf_msisdns_list:
                change_profile_response = self.change_profile_for_vodafone_recipients(vf_msisdns_list)
                if not change_profile_response:
                    return False
            elif not wallets_moderator.change_profile or (wallets_moderator.change_profile and not vf_msisdns_list):
                self.doc_obj.has_change_profile_callback = True
                self.doc_obj.txn_id = None
                self.doc_obj.processed_successfully()

            # 7.1 For normal flow sheets: Save the refined data as disbursement data records
            if self.is_normal_sheet_specs:
                records = zip(amounts_list, msisdn_list)
                objs = [
                    DisbursementData(doc=self.doc_obj, amount=float(record[0]), msisdn=record[1]) for record in records
                ]
                DisbursementData.objects.bulk_create(objs=objs)

            # 7.2 For issuer based sheets: Save the refined data as disbursement data records
            else:
                records = zip(amounts_list, msisdn_list, issuers_list)
                objs = [
                    DisbursementData(
                            doc=self.doc_obj, amount=float(record[0]), msisdn=record[1], issuer=record[2]
                    ) for record in records
                ]
                DisbursementData.objects.bulk_create(objs=objs)

            self.doc_obj.save()
            notify_maker(self.doc_obj)
            UPLOAD_LOGGER.debug(f"[message] [e wallets file passed processing] [celery_task] -- Doc id: {doc_id}")
            return True
        except Doc.DoesNotExist:
            UPLOAD_LOGGER.\
                debug(f"[message] [ewallets file processing error] [celery_task] -- Doc id: {doc_id} not found")
            return False
        except Exception as err:
            self.end_with_failure(MSG_REGISTRATION_PROCESS_ERROR)
            UPLOAD_LOGGER.debug(f"[message] [ewallets file processing error] [celery_task] -- {err.args}")
            return False


class ExportClientsTransactionsMonthlyReportTask(Task):
    """
    Task to export clients transactions monthly reports.
    """

    superadmin_user = None
    start_date = None
    end_date = None
    first_day = None
    last_day = None

    def refine_first_and_end_date_format(self):
        """
        Refine start date and end date format using datetime and set values for first and last days.
        make_aware(): Converts naive datetime object (without timezone info) to the one that has timezone info,
            using timezone specified in your django settings if you don't specify it explicitly as a second argument.
        """
        first_day = datetime(
                year=int(self.start_date.split('-')[0]),
                month=int(self.start_date.split('-')[1]),
                day=int(self.start_date.split('-')[2]),
        )
        self.first_day = make_aware(first_day)

        last_day = datetime(
                year=int(self.end_date.split('-')[0]),
                month=int(self.end_date.split('-')[1]),
                day=int(self.end_date.split('-')[2]),
                hour=23,
                minute=59,
                second=59,
        )
        self.last_day = make_aware(last_day)

    def _add_admin_username_to_qs_values(self, qs, checkers_parent_username):
        """Append admin username to the output transactions queryset values dict"""
        for q in qs:
            if len(str(q['issuer'])) > 20:
                q['issuer'] = 'C'
            elif q['issuer'] != AbstractBaseIssuer.BANK_WALLET and len(q['issuer']) == 1:
                q['issuer'] = str(dict(AbstractBaseIssuer.ISSUER_TYPE_CHOICES)[q['issuer']]).lower()

            q['admin'] = checkers_parent_username[q['checker']]
        return qs

    def _add_vf_facilitator_identifier_to_qs_values(self,
                                                    qs,
                                                    checkers_parent_username,
                                                    admins_vf_facilitator_identifier):
        """Append vodafone facilitator identifier to the output transactions queryset values dict"""
        for q in qs:
            q['vf_facilitator_identifier'] = admins_vf_facilitator_identifier[checkers_parent_username[q['checker']]]
            q['full_date'] = f"{self.start_date} to {self.end_date}"
        return qs

    def _calculate_and_add_fees_to_qs_values(self, qs):
        """Calculate and append the fees to the output transactions queryset values dict"""
        for q in qs:
            q['fees'], q['vat'] = Budget.objects.get(disburser__username=q['admin']).\
                                      calculate_fees_and_vat_for_amount(q['total'], q['issuer'], q['count'])
        return qs

    def _add_issuers_with_values_0_to_final_data(self, final_data, issuers_exist):
        for key in final_data.keys():
            for el in final_data[key]:
                if el['issuer'] != 'total':
                    issuers_exist[el['issuer']] = True
            for issuer in issuers_exist.keys():
                if not issuers_exist[issuer]:
                    default_issuer_dict = {'issuer': issuer, 'count': 0, 'total': 0}
                    if not self.superadmin_user.is_vodafone_facilitator_onboarding:
                        default_issuer_dict['fees'] = 0
                        default_issuer_dict['vat'] = 0
                    final_data[key].append(default_issuer_dict)

        return final_data

    def aggregate_vf_ets_aman_transactions(self,
                                           checkers_qs,
                                           checkers_parent_username,
                                           checkers_parent_vf_facilitator_identifier):
        """Calculate vodafone, etisalat, aman transactions details from DisbursementData model"""
        qs = DisbursementData.objects.filter(
                Q(created_at__gte=self.first_day),
                Q(created_at__lte=self.last_day),
                Q(reason__exact='SUCCESS'),
                Q(doc__disbursed_by__in=checkers_qs)
        ).annotate(checker=F('doc__disbursed_by__username')).values('checker', 'issuer').\
            annotate(total=Sum('amount'), count=Count('id'))

        qs = self._add_admin_username_to_qs_values(qs, checkers_parent_username)

        if self.superadmin_user.is_vodafone_facilitator_onboarding:
            qs = self._add_vf_facilitator_identifier_to_qs_values(
                    qs,
                    checkers_parent_username,
                    checkers_parent_vf_facilitator_identifier
            )
        else:
            qs = self._calculate_and_add_fees_to_qs_values(qs)
        return qs

    def aggregate_bank_wallets_orange_instant_transactions(self, checkers_qs, checkers_parent_username):
        """Calculate bank wallets, orange, instant transactions details from InstantTransaction model"""
        qs = InstantTransaction.objects.filter(
                Q(created_at__gte=self.first_day),
                Q(created_at__lte=self.last_day),
                Q(status=AbstractBaseStatus.SUCCESSFUL),
                Q(document__disbursed_by__in=checkers_qs) | Q(from_user__in=checkers_qs)
                ).annotate(
                checker=Case(
                        When(from_user__isnull=False, then=F('from_user__username')),
                        default=F('document__disbursed_by__username')
                )
        ).extra(select={'issuer': 'issuer_type'}).values('checker', 'issuer').\
            annotate(total=Sum('amount'), count=Count('uid'))

        qs = self._add_admin_username_to_qs_values(qs, checkers_parent_username)
        qs = self._calculate_and_add_fees_to_qs_values(qs)
        return qs

    def aggregate_bank_cards_transactions(self, checkers_qs, checkers_parent_username):
        """Calculate bank cards transactions details from BankTransaction model"""
        qs = BankTransaction.objects.filter(
                Q(created_at__gte=self.first_day),
                Q(created_at__lte=self.last_day),
                Q(status=AbstractBaseStatus.SUCCESSFUL),
                Q(document__disbursed_by__in=checkers_qs) | Q(user_created__in=checkers_qs)
        ).annotate(
                checker=Case(
                        When(document__disbursed_by__isnull=False, then=F('document__disbursed_by__username')),
                        default=F('user_created__username')
                )
        ).extra(select={'issuer': 'transaction_id'}).values('checker', 'issuer').\
            annotate(total=Sum('amount'), count=Count('id'))

        qs = self._add_admin_username_to_qs_values(qs, checkers_parent_username)
        qs = self._calculate_and_add_fees_to_qs_values(qs)
        return qs

    def group_result_transactions_data(self, vf_ets_aman_qs, bank_wallets_orange_instant_qs, cards_qs):
        """Group all data by admin"""
        transactions_details_list = [vf_ets_aman_qs, bank_wallets_orange_instant_qs, cards_qs]
        final_data = dict()

        for transactions_result_type in transactions_details_list:
            for q in transactions_result_type:
                if q['admin'] in final_data:
                    issuer_exist = False
                    for admin_q in final_data[q['admin']]:
                        if q['issuer'] == admin_q['issuer']:
                            admin_q['total'] += q['total']
                            admin_q['count'] += q['count']
                            if not self.superadmin_user.is_vodafone_facilitator_onboarding:
                                admin_q['fees'] += q['fees']
                                admin_q['vat'] += q['vat']
                            issuer_exist = True
                            break
                    if not issuer_exist:
                        final_data[q['admin']].append(q)
                else:
                    final_data[q['admin']] = [q]

        return final_data

    def write_data_to_excel_file(self, final_data, column_names_list, distinct_msisdn=None):
        """Write exported transactions data to excel file"""
        filename = _(f"clients_monthly_report_{self.start_date}_{self.end_date}_{randomword(4)}.xls")
        file_path = f"{settings.MEDIA_ROOT}/documents/disbursement/{filename}"
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('report')

        # 1. Write sheet header/column names - first row
        row_num = 0
        font_style = xlwt.XFStyle()
        font_style.font.bold = True

        for col_nums in range(len(column_names_list)):
            ws.write(row_num, col_nums, column_names_list[col_nums], font_style)

        # 2. Write sheet body/data - remaining rows
        font_style = xlwt.XFStyle()
        row_num += 1

        if not self.superadmin_user.is_vodafone_facilitator_onboarding:
            col_nums = {
                'total': 2,
                'vodafone': 3,
                'etisalat': 4,
                'aman': 5,
                'orange': 6,
                'B': 7,
                'C': 8
            }
            for key in final_data.keys():
                ws.write(row_num, 0, key, font_style)
                ws.write(row_num, 1, 'Volume', font_style)
                ws.write(row_num+1, 1, 'Count', font_style)
                ws.write(row_num+2, 1, 'Fees', font_style)
                ws.write(row_num+3, 1, 'Vat', font_style)

                for el in final_data[key]:
                    ws.write(row_num, col_nums[el['issuer']], el['total'], font_style)
                    ws.write(row_num+1, col_nums[el['issuer']], el['count'], font_style)
                    ws.write(row_num+2, col_nums[el['issuer']], el['fees'], font_style)
                    ws.write(row_num+3, col_nums[el['issuer']], el['vat'], font_style)

                row_num += 4
        else:
            for key in final_data.keys():
                current_admin_report = final_data[key][0]
                ws.write(row_num, 0, key, font_style)
                ws.write(row_num, 1, current_admin_report['count'], font_style)
                ws.write(row_num, 2, current_admin_report['total'], font_style)
                ws.write(row_num, 3, len(distinct_msisdn[key]), font_style)
                ws.write(row_num, 4, current_admin_report['full_date'], font_style)
                ws.write(row_num, 5, current_admin_report['vf_facilitator_identifier'], font_style)
                row_num += 1

        wb.save(file_path)
        report_download_url = f"{settings.BASE_URL}{str(reverse('disbursement:download_exported'))}?filename={filename}"
        return report_download_url

    def prepare_transactions_report(self):
        """Prepare report for transactions related to client"""
        # 1. Format start and end date
        self.refine_first_and_end_date_format()

        # 2. Get all clients of the current superadmin
        admins_qs = self.superadmin_user.children()

        # 3. Get all children [checkers/api checkers] for every client at the clients list
        checkers_qs = []
        checkers_parent_username = {}
        admins_vf_facilitator_identifier = {}
        for admin in admins_qs:
            admins_vf_facilitator_identifier[admin.username] = admin.client.vodafone_facilitator_identifier
            admin_children_list = admin.children()
            for child in admin_children_list:
                if child.is_checker or child.is_instantapichecker:
                    checkers_qs.append(child)
                    checkers_parent_username[child.username] = admin.username

        # 4. Calculate vodafone, etisalat, aman transactions details
        vf_ets_aman_qs = self.aggregate_vf_ets_aman_transactions(
                checkers_qs, checkers_parent_username, admins_vf_facilitator_identifier
        )

        bank_wallets_orange_instant_transactions_qs = []
        bank_cards_transactions_qs = []

        if not self.superadmin_user.is_vodafone_facilitator_onboarding:
            # 5. Calculate bank wallets, orange, instant transactions details
            bank_wallets_orange_instant_transactions_qs = self.aggregate_bank_wallets_orange_instant_transactions(
                    checkers_qs, checkers_parent_username
            )

            # 6. Calculate bank cards/accounts transactions details
            bank_cards_transactions_qs = self.aggregate_bank_cards_transactions(checkers_qs, checkers_parent_username)

        # 7. Group all data by admin
        final_data = self.group_result_transactions_data(
                vf_ets_aman_qs, bank_wallets_orange_instant_transactions_qs, bank_cards_transactions_qs
        )

        if not self.superadmin_user.is_vodafone_facilitator_onboarding:
            # 8. Calculate total volume, count, fees for each admin
            for key in final_data.keys():
                total_per_admin = {
                    'admin': key,
                    'issuer': 'total',
                    'total': round(Decimal(0), 2),
                    'count': round(Decimal(0), 2),
                    'fees': round(Decimal(0), 2),
                    'vat': round(Decimal(0), 2)
                }
                for el in final_data[key]:
                    total_per_admin['total'] += round(Decimal(el['total']), 2)
                    total_per_admin['count'] += el['count']
                    total_per_admin['fees'] += el['fees']
                    total_per_admin['vat'] += el['vat']
                final_data[key].append(total_per_admin)

        # 9. Add issuer with values 0 to final data
        if self.superadmin_user.is_vodafone_facilitator_onboarding:
            issuers_exist = {
                'default': False,
            }
        else:
            issuers_exist = {
                'vodafone': False,
                'etisalat': False,
                'aman': False,
                'orange': False,
                'B': False,
                'C': False
            }

        final_data = self._add_issuers_with_values_0_to_final_data(final_data, issuers_exist)

        # 10. Add all admin that have no transactions
        for current_admin in admins_qs:
            if not current_admin.username in final_data.keys():
                if self.superadmin_user.is_vodafone_facilitator_onboarding:
                    final_data[current_admin.username] = [{
                        **DEFAULT_PER_ADMIN_FOR_VF_FACILITATOR_TRANSACTIONS_REPORT,
                        'full_date': f"{self.start_date} to {self.end_date}",
                        'vf_facilitator_identifier': admins_vf_facilitator_identifier[current_admin.username]
                    }]
                else:
                    final_data[current_admin.username] = DEFAULT_LIST_PER_ADMIN_FOR_TRANSACTIONS_REPORT

        if self.superadmin_user.is_vodafone_facilitator_onboarding:
            # 11. calculate distinct msisdn per admin
            distinct_msisdn = dict()
            for el in vf_ets_aman_qs.values():
                if checkers_parent_username[el['checker']] in distinct_msisdn:
                    distinct_msisdn[checkers_parent_username[el['checker']]].add(el['msisdn'])
                else:
                    distinct_msisdn[checkers_parent_username[el['checker']]] = set([el['msisdn']])

            # 12. Add all admin that have no transactions to distinct msisdn
            for current_admin in admins_qs:
                if not current_admin.username in distinct_msisdn.keys():
                    distinct_msisdn[current_admin.username] = set([])

            column_names_list = [
                'Account Name ', 'Total Count', 'Total Amount', 'Distinct Receivers', 'Full Date', 'Billing Number'
            ]
            return self.write_data_to_excel_file(final_data, column_names_list, distinct_msisdn)
        else:
            column_names_list = [
                'Clients', '', 'Total', 'Vodafone', 'Etisalat', 'Aman', 'Orange', 'Bank Wallets', 'Bank Accounts/Cards'
            ]
            # 13. Write final data to excel file
            return self.write_data_to_excel_file(final_data, column_names_list)

    def prepare_and_send_report_mail(self, report_download_url):
        """Prepare the mail to be sent with the report download link"""
        mail_subject = f' {self.superadmin_user.get_full_name} Clients Transactions Report ' \
                       f'From {self.start_date} To {self.end_date}'
        mail_content_message = _(
                f"Dear <strong>{self.superadmin_user.get_full_name}</strong><br><br>You can download "
                f"transactions report of your clients within the period of {self.start_date} to {self.end_date} "
                f"from here <a href='{report_download_url}' >Download</a>.<br><br>Best Regards,"
        )
        deliver_mail(self.superadmin_user, _(mail_subject), mail_content_message)

    def run(self, user_id, start_date, end_date, *args, **kwargs):
        self.superadmin_user = User.objects.get(id=user_id)
        self.start_date = start_date
        self.end_date = end_date
        report_download_url = self.prepare_transactions_report()
        self.prepare_and_send_report_mail(report_download_url)
        return True


BankWalletsAndCardsSheetProcessor = app.register_task(BankWalletsAndCardsSheetProcessor())
EWalletsSheetProcessor = app.register_task(EWalletsSheetProcessor())
ExportClientsTransactionsMonthlyReportTask = app.register_task(ExportClientsTransactionsMonthlyReportTask())


@app.task()
def handle_change_profile_callback(doc_id, transactions):
    """
    Related to disbursement
    Background task for handling central callback of msisdns change profile process
    :param doc_id: Id of the doc which holds the msisdns
    :param transactions: The callback dictionary from the central
    :return:
    """
    doc_obj = Doc.objects.get(id=doc_id)
    doc_obj.has_change_profile_callback = True
    msisdns, errors = [], []
    has_error = False

    for msisdn, status_code, msg_list in transactions:
        if status_code not in ["200", "629", "560", "562"]:
            has_error = True
            errors.append('\n'.join(msg_list))
        else:
            errors.append("Passed validations successfully")
        msisdns.append(msisdn)

    if not has_error:
        doc_obj.processed_successfully()
        notify_maker(doc_obj)
        return

    doc_obj.disbursement_data.all().delete()
    filename = f"failed_disbursement_validation_{randomword(4)}.xlsx"
    file_path = f"{settings.MEDIA_ROOT}/documents/disbursement/{filename}"

    data = list(zip(msisdns, errors))
    headers = ['Mobile Number', 'Error']
    data.insert(0, headers)
    export_excel(file_path, data)
    download_url = settings.BASE_URL + \
        str(reverse('disbursement:download_validation_failed', kwargs={'doc_id': doc_id})) + f"?filename={filename}"

    doc_obj.processing_failure("Mobile numbers validation error")
    notify_maker(doc_obj, download_url)
    return


def prepare_disbursed_data_report(doc_id, report_type):
    """Prepare report for all, failed or success document transactions"""
    doc_obj = Doc.objects.get(id=doc_id)

    if report_type == 'all':
        filename = _('disbursed_data_%s_%s.xlsx') % (str(doc_id), randomword(4))
        resource_query_dict = {'doc': doc_obj, 'is_disbursed': None}
    elif report_type == 'success':
        filename = _(f"success_disbursed_{str(doc_id)}_{str(doc_id)}.xlsx")
        resource_query_dict = {'doc': doc_obj, 'is_disbursed': True}
    else:
        filename = _(f"failed_disbursed_{str(doc_id)}_{randomword(4)}.xlsx")
        resource_query_dict = {'doc': doc_obj, 'is_disbursed': False}

    if doc_obj.is_e_wallet:
        dataset = DisbursementDataResourceForEWallets(**resource_query_dict)
    elif doc_obj.is_bank_wallet:
        dataset = DisbursementDataResourceForBankWallet(**resource_query_dict)
    elif doc_obj.is_bank_card:
        dataset = DisbursementDataResourceForBankCards(**resource_query_dict)

    dataset = dataset.export()
    file_path = f"{settings.MEDIA_ROOT}/documents/disbursement/{filename}"

    with open(file_path, "wb") as f:
        f.write(dataset.xlsx)

    report_view_url = settings.BASE_URL + str(reverse('disbursement:disbursed_data', kwargs={'doc_id': doc_id}))
    report_download_url = settings.BASE_URL + \
                   str(reverse('disbursement:download_failed', kwargs={'doc_id': doc_id})) + f"?filename={filename}"

    return doc_obj, report_view_url, report_download_url


@app.task()
@respects_language
def generate_failed_disbursed_data(doc_id, user_id, **kwargs):
    """
    Related to disbursement
    :param doc_id:
    :param user_id:
    :param kwargs:
    :return:
    """
    doc_obj, report_view_url, report_download_url = prepare_disbursed_data_report(doc_id, 'failed')
    user = User.objects.get(id=user_id)
    message = _(f"""Dear <strong>{str(user.first_name).capitalize()}</strong><br><br>
        You can download the failed disbursement data related to this document
        <a href="{report_view_url}" >{doc_obj.filename()}</a>
        from here <a href="{report_download_url}" >Download</a><br><br>
        Thanks, BR""")
    deliver_mail(user, _(' Failed Disbursement File Download'), message)


@app.task()
@respects_language
def generate_success_disbursed_data(doc_id, user_id, **kwargs):
    """
    Related to disbursement
    :param doc_id:
    :param user_id:
    :param kwargs:
    :return:
    """
    doc_obj, report_view_url, report_download_url = prepare_disbursed_data_report(doc_id, 'success')
    user = User.objects.get(id=user_id)
    message = _(f"""Dear <strong>{str(user.first_name).capitalize()}</strong><br><br>
        You can download the success disbursement data related to this document
        <a href="{report_view_url}" >{doc_obj.filename()}</a>
        from here <a href="{report_download_url}" >Download</a><br><br>
        Thanks, BR""")
    deliver_mail(user, _(' Success Disbursement File Download'), message)


@app.task()
@respects_language
def generate_all_disbursed_data(doc_id, user_id, **kwargs):
    """
    Related to disbursement
    Generate success and failed excel sheet from already disbursed data
    """
    doc_obj, report_view_url, report_download_url = prepare_disbursed_data_report(doc_id, 'all')
    user = User.objects.get(id=user_id)
    message = _(f"""Dear <strong>{str(user.first_name).capitalize()}</strong><br><br>
        You can download the disbursement data related to this document
        <a href="{report_view_url}" >{doc_obj.filename()}</a>
        from here <a href="{report_download_url}" >Download</a><br><br>
        Thanks, BR""")
    deliver_mail(user, _(' Disbursement Data File Download'), message)


@app.task(ignore_result=False)
@respects_language
def handle_uploaded_file(doc_obj_id, **kwargs):
    """
    Related to collection
    A function that parse the document and save it into the File Data
    It has 3 cases :
    Category has files so check if draft or delete stale data
    Category has no files

    :param doc_obj_id: uploaded file id.
    """
    doc_obj = Doc.objects.get(id=doc_obj_id)
    format = doc_obj.format
    xl_workbook = xlrd.open_workbook(doc_obj.file.path)
    collection_data = doc_obj.collection_data
    # Process excel file row by row.
    xl_sheet = xl_workbook.sheet_by_index(0)
    row_index = 0
    for row in xl_sheet.get_rows():
        if row_index:
            data = tablib.Dataset(headers=format.identifiers())
            excl_data = []
            for cell in row:
                if cell.ctype == 3:  # Date
                    try:
                        cell.value = xlrd.xldate.xldate_as_datetime(cell.value, 0).date().strftime('%d-%m-%Y')
                        excl_data.append(cell.value)

                    except ValueError:
                        excl_data.append(cell.value)

                elif cell.ctype == 2:  # Number
                    val = str(cell.value).split(".")
                    if val[1] == '0':
                        excl_data.append(val[0])
                    else:
                        excl_data.append(str(cell.value))
                else:
                    if re.match(r'\s*(?P<d>\d\d?)(?P<sep>\D)(?P<m>\d\d?)(?P=sep)(?P<Y>\d\d\d\d)', cell.value):
                        cell.value = re.sub('[/.:]', '-', cell.value)

                    elif cell.value.startswith('`'):
                        cell.value = cell.value.split('`')[-1]

                    excl_data.append(str(cell.value))
        else:
            row_index += 1
            continue

        # *map(data.append, [excl_data, ]),

        # Specify unique fields to search with.
        processed_data = json.loads(data.json)[0]
        search_dict = {
            'data__%s' % collection_data.unique_field: processed_data[collection_data.unique_field],
            'user__hierarchy': collection_data.user.hierarchy,
            'is_draft': False,
        }
        creation_dict = {
            'user': collection_data.user,
            'is_draft': False,
            'doc': doc_obj,
            'data': processed_data
        }
        # Creates if no records, updates if record with partial exists, skip otherwise.
        file_data = FileData.objects.filter(**search_dict)
        if not file_data:
            file_data = FileData.objects.create(**creation_dict)
        else:
            records_to_be_updated = file_data.filter(has_full_payment=False).first()
            try:
                records_to_be_updated.data = processed_data
                file_data = records_to_be_updated
                records_to_be_updated.save()
            except AttributeError:
                file_data = file_data.first()

        try:
            if collection_data.date_field:
                file_data.date = parse(file_data.data[collection_data.date_field]).date()
            else:
                file_data.date = parse(file_data.data['due_date']).date()
        except (KeyError, ValueError):
            file_data.date = datetime.now()
        file_data.save()

    doc_obj.processed_successfully()
    notify_makers_collection(doc_obj)


@app.task()
@respects_language
def notify_checkers(doc_id, level, **kwargs):
    """
    Related to disbursement
    Background task to send email to the next level of checkers that this is your turn to review the file
    :param doc_id: the id of the document which needs to be reviewed
    :param level: Level of authoritative checkers, that determines which level has to review the file
    :param kwargs: Any other kwargs
    :return:
    """
    doc_obj = Doc.objects.get(id=doc_id)
    checkers = CheckerUser.objects.filter(hierarchy=doc_obj.owner.hierarchy).filter(level__level_of_authority=level)

    if not checkers.exists():
        return

    doc_view_url = settings.BASE_URL + doc_obj.get_absolute_url()
    message = _(f"""Dear <strong>Checker</strong><br><br>
        The file named <a href="{doc_view_url}" >{doc_obj.filename()}</a> is ready for review<br><br>
        Thanks, BR""")
    deliver_mail(None, _(' Review Notification'), message, checkers)

    CHECKERS_NOTIFICATION_LOGGER.debug(
            f"[message] [REVIEWERS NOTIFIED] [{doc_obj.owner}] -- "
            f"{' and '.join([checker.username for checker in checkers])}"
    )


@app.task()
@respects_language
def notify_disbursers(doc_id, min_level, **kwargs):
    """
    Related to disbursement
    Background task to send email to notify all levels of authoritative checkers that the file is ready for disbursement
    :param doc_id: the id of the document which passed the needed reviews successfully and is ready for disbursement
    :param min_level: Minimum level of authoritative checkers
    :param kwargs: Any other kwargs
    :return:
    """
    doc_obj = Doc.objects.get(id=doc_id)
    disbursers_to_be_notified = CheckerUser.objects.\
        filter(hierarchy=doc_obj.owner.hierarchy).filter(level__level_of_authority__gte=min_level)

    if not disbursers_to_be_notified.exists():
        return

    doc_view_url = settings.BASE_URL + doc_obj.get_absolute_url()
    message = _(f"""Dear <strong>Checker</strong><br><br>
        The file named <a href="{doc_view_url}" >{doc_obj.filename()}</a> is ready for disbursement<br><br>
        Thanks, BR""")
    deliver_mail(None, _(' Disbursement Notification'), message, disbursers_to_be_notified)

    CHECKERS_NOTIFICATION_LOGGER.debug(
            f"[message] [DISBURSERS NOTIFIED] [{doc_obj.owner}] -- "
            f"{' and '.join([checker.username for checker in disbursers_to_be_notified])}"
    )


@app.task()
@respects_language
def doc_review_maker_mail(doc_id, review_id, **kwargs):
    """
    Related to disbursement
    Background task to send mail to maker users after the reviews have been completed
    :param doc_id:
    :param review_id:
    :param kwargs:
    :return:
    """
    doc = Doc.objects.get(id=doc_id)
    review = doc.reviews.get(id=review_id)
    maker = doc.owner
    doc_view_url = settings.BASE_URL + doc.get_absolute_url()

    if doc.is_e_wallet:
        reviews_required = doc.file_category.no_of_reviews_required
    else:
        all_categories = doc.owner.root.file_category.all()
        reviews_required = min([cat.no_of_reviews_required for cat in all_categories])

    if review.is_ok:
        message = _(f"""Dear <strong>{str(maker.first_name).capitalize()}</strong><br><br>
            The file named <a href="{doc_view_url}" >{doc.filename()}</a> passed the review
             number {doc.reviews.filter(is_ok=True).count()} out of {reviews_required} by
            the checker: {review.user_created.first_name} {review.user_created.last_name}<br><br>
            Thanks, BR""")
    else:
        message = _(f"""Dear <strong>{str(maker.first_name).capitalize()}</strong><br><br>
                    The file named <a href="{doc_view_url}" >{doc.filename()}</a> did not pass the review by
                    the checker: {review.user_created.first_name} {review.user_created.last_name}
                    and the reason is: {review.comment}<br><br>
                    Thanks, BR""")
    deliver_mail(maker, _(' File Review Notification'), message)


def notify_maker(doc, download_url=None):
    """
    Related to disbursement
    :param doc:
    :param download_url:
    :return:
    """
    maker = doc.owner
    doc_view_url = settings.BASE_URL + doc.get_absolute_url()
    message_intro = f"Dear <strong>{str(maker.first_name).capitalize()}</strong><br><br>" + \
                    f"The file named <a href='{doc_view_url}'>{doc.filename()}</a>"

    if doc.is_processed:
        message = _(f"{message_intro} validated successfully. You can notify checkers now.<br><br>Thanks, BR")
    else:
        MSG = _(f"{message_intro} failed validations.<br><br>The reason is: {doc.processing_failure_reason}.<br><br>")

        if download_url:
            MSG = _(f"{MSG}You can download the file containing errors from <a href='{download_url}'>here.</a><br><br>")
        message = _(f"{MSG}Thanks, BR")

    deliver_mail(maker, _(' File Upload Notification'), message)


def notify_makers_collection(doc):
    makers = UploaderUser.objects.filter(hierarchy=doc.owner.hierarchy)
    doc_view_url = settings.BASE_URL + doc.get_absolute_url()
    message = _(f"""Dear <strong>Maker</strong><br><br>
        The file named <a href="{doc_view_url}" >{doc.filename()}</a> was validated successfully<br><br>
        Thanks, BR""")
    deliver_mail(None, _(' Collection File Upload Notification'), message, makers)
