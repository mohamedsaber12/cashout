# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import logging

from django.db.models import Q
from django.utils import timezone
from django.core.paginator import Paginator

from core.models import AbstractBaseStatus
from data.decorators import respects_language
from disbursement.models import BankTransaction
from instant_cashin.models.instant_transactions import InstantTransaction
from payouts.settings.celery import app

from .specific_issuers_integrations import BankTransactionsChannel
import requests
from celery.task import control
from instant_cashin.utils import get_from_env
from django.core.mail import EmailMultiAlternatives
from django.conf import settings


ACH_GET_TRX_STATUS_LOGGER = logging.getLogger("ach_get_transaction_status")
TIMEOUTS_UPDATE_LOGGER = logging.getLogger("timeouts_updates")


@app.task()
@respects_language
def check_for_status_updates_for_latest_bank_transactions(days_delta=6, **kwargs):
    """Task for updating pending bank transactions from EBC for the last 5 days at max"""

    # check if EBC is up , if not return False
    if get_from_env("ENVIRONMENT") != "staging":
        try:
            requests.get("https://cibcorpay.egyptianbanks.net", timeout=10)
        except Exception as e:
            ACH_GET_TRX_STATUS_LOGGER.debug(
                f"[message] [check for EBC status] [celery_task] -- " f"Exeption: {e}"
            )
            return False
        # check if there's same task is running
        active_tasks = control.inspect().active()
        ach_worker = get_from_env("ach_worker")
        ACH_GET_TRX_STATUS_LOGGER.debug(f"Active Tasks {active_tasks.get(ach_worker)}")
        num_of_current_tasks = 0
        for tsk in active_tasks.get(ach_worker):
            if (
                tsk["type"]
                == "instant_cashin.tasks.check_for_status_updates_for_latest_bank_transactions"
            ):
                num_of_current_tasks += 1
            if (
                tsk["type"]
                == "instant_cashin.tasks.check_for_status_updates_for_latest_bank_transactions_more_than_6_days"
            ):
                return False
        if num_of_current_tasks > 1:
            return False

    try:
        five_days_ago = timezone.now() - datetime.timedelta(int(days_delta))
        latest_bank_trx_ids = (
            BankTransaction.objects.filter(Q(created_at__gte=five_days_ago))
            .order_by("parent_transaction__transaction_id", "-id")
            .distinct("parent_transaction__transaction_id")
            .values_list("id", flat=True)
        )
        latest_bank_transactions = (
            BankTransaction.objects.filter(id__in=latest_bank_trx_ids)
            .filter(
                Q(status=AbstractBaseStatus.PENDING)
                | Q(status=AbstractBaseStatus.SUCCESSFUL)
            )
            .filter(~Q(transaction_status_code=8333))
            .order_by("created_at")
        )

        if latest_bank_transactions.count() > 0:
            ACH_GET_TRX_STATUS_LOGGER.debug(
                f"[message] [check for trx update task] [celery_task] -- "
                f"transactions count: {latest_bank_transactions.count()}"
            )
            paginator = Paginator(latest_bank_transactions, 500)
            for page_number in paginator.page_range:
                queryset = paginator.page(page_number)
                for bank_trx in queryset:
                    if not bank_trx.parent_transaction.is_manual_batch:
                        BankTransactionsChannel.get_transaction_status(bank_trx)
        return True
    except (BankTransaction.DoesNotExist, ValueError, Exception) as e:
        ACH_GET_TRX_STATUS_LOGGER.debug(f"check for EBC status Error {e}")
        return False


@app.task()
@respects_language
def check_for_status_updates_for_latest_bank_transactions_more_than_6_days():
    # check if EBC is up , if not return False
    if get_from_env("ENVIRONMENT") != "staging":
        try:
            requests.get("https://cibcorpay.egyptianbanks.net", timeout=10)
        except Exception as e:
            ACH_GET_TRX_STATUS_LOGGER.debug(
                f"[message] [check for EBC status more than 6 days] [celery_task] -- "
                f"Exeption: {e}"
            )
            return False
        active_tasks = control.inspect().active()
        ach_worker = get_from_env("ach_worker")
        ACH_GET_TRX_STATUS_LOGGER.debug(f"Active Tasks {active_tasks.get(ach_worker)}")
        num_of_current_tasks = 0
        for tsk in active_tasks.get(ach_worker):
            if (
                tsk["type"]
                == "instant_cashin.tasks.check_for_status_updates_for_latest_bank_transactions_more_than_6_days"
            ):
                num_of_current_tasks += 1
            if (
                tsk["type"]
                == "instant_cashin.tasks.check_for_status_updates_for_latest_bank_transactions"
            ):
                return False
    try:
        start_date = timezone.now()
        end_date = timezone.now() - datetime.timedelta(int(16))
        latest_bank_trx_ids = (
            BankTransaction.objects.filter(Q(created_at__gte=end_date))
            .filter(Q(created_at__lte=start_date))
            .order_by("parent_transaction__transaction_id", "-id")
            .distinct("parent_transaction__transaction_id")
            .values_list("id", flat=True)
        )
        latest_bank_transactions = (
            BankTransaction.objects.filter(id__in=latest_bank_trx_ids)
            .filter(
                Q(status=AbstractBaseStatus.PENDING)
                | Q(status=AbstractBaseStatus.SUCCESSFUL)
            )
            .filter(~Q(transaction_status_code=8333))
            .order_by("created_at")
        )

        if latest_bank_transactions.count() > 0:
            ACH_GET_TRX_STATUS_LOGGER.debug(
                f"[message] [check for trx update task] [celery_task] -- "
                f"transactions count: {latest_bank_transactions.count()}"
            )
            paginator = Paginator(latest_bank_transactions, 500)
            for page_number in paginator.page_range:
                queryset = paginator.page(page_number)
                for bank_trx in queryset:
                    if not bank_trx.parent_transaction.is_manual_batch:
                        BankTransactionsChannel.get_transaction_status(bank_trx)
        return True
    except (BankTransaction.DoesNotExist, ValueError, Exception) as e:
        ACH_GET_TRX_STATUS_LOGGER.debug(
            f"check for EBC status more than 6 days Error {e}"
        )
        return False


@app.task()
def update_instant_timeouts_from_vodafone_report(
    vodafone_data, start_date, end_date, email_notify=None
):
    TIMEOUTS_UPDATE_LOGGER.debug(
        f"[Timeouts updates start_date : {start_date} end_date {end_date} email for {email_notify}"
    )
    issuer_mapper = {
        "V": "vodafone",
        "E": "etisalat",
        "O": "orange",
        "B": "bank_wallet",
    }
    date_range = (
        datetime.datetime.combine(
            datetime.datetime.strptime(start_date, "%Y-%m-%d").date(),
            datetime.time.min,
        ),
        datetime.datetime.combine(
            datetime.datetime.strptime(end_date, "%Y-%m-%d").date(),
            datetime.time.max,
        ),
    )
    trns = InstantTransaction.objects.filter(
        disbursed_date__range=date_range,
        status="U",
        transaction_status_code__in=[6005, 501, 408],
    )
    total_timeouts = trns.count()
    total_failed = 0
    total_success = 0
    for trn in trns:
        if trn.reference_id:
            if trn.reference_id in vodafone_data:
                if vodafone_data[trn.reference_id]["success"]:
                    TIMEOUTS_UPDATE_LOGGER.debug(
                        f"[Timeouts updates] update transaction {trn.uid} and ref {trn.reference_id} with Succesful status"
                    )
                    trn.status = "S"
                    trn.transaction_status_code = "200"
                    trn.transaction_status_description = (
                        "تم ايداع "
                        + str(trn.amount)
                        + " جنيه إلى رقم "
                        + str(trn.anon_recipient)
                        + "بنجاح"
                    )
                    trn.save()
                    # update budget
                    amount_plus_fees_vat = (
                        trn.from_user.root.budget.release_hold_balance(
                            trn.amount, issuer_mapper[trn.issuer_type]
                        )
                    )
                    trn.balance_after = trn.balance_before - amount_plus_fees_vat
                    trn.save()
                    total_success = total_success + 1
                else:
                    TIMEOUTS_UPDATE_LOGGER.debug(
                        f"[Timeouts updates] [found on report ] update transaction {trn.uid} and ref {trn.reference_id} with failed status"
                    )
                    trn.status = "F"
                    trn.from_user.root.budget.return_hold_balance(
                        trn.amount, issuer_mapper[trn.issuer_type]
                    )
                    trn.save()
                    total_failed = total_failed + 1
                    if trn.from_accept == 'single':
                        current_amount_plus_fess_and_vat = trn.from_user.root.budget.accumulate_amount_with_fees_and_vat(trn.amount, issuer_mapper[trn.issuer_type])
                        revert_balance_payload = {
                            "transaction_id": trn.accept_balance_transfer_id,
                            "fees_amount_cents": "0",
                        }
                        revert_balance_to_accept_account(
                            revert_balance_payload,
                            trn.from_user,
                            current_amount_plus_fess_and_vat,
                        )

            else:
                TIMEOUTS_UPDATE_LOGGER.debug(
                    f"[Timeouts updates] [not found on report ] update transaction {trn.uid} and ref {trn.reference_id} with failed status"
                )
                trn.status = "F"
                trn.from_user.root.budget.return_hold_balance(
                    trn.amount, issuer_mapper[trn.issuer_type]
                )
                trn.save()
                total_failed = total_failed + 1
                if trn.from_accept == 'single':
                    current_amount_plus_fess_and_vat = trn.from_user.root.budget.accumulate_amount_with_fees_and_vat(trn.amount, issuer_mapper[trn.issuer_type])
                    revert_balance_payload = {
                        "transaction_id": trn.accept_balance_transfer_id,
                        "fees_amount_cents": "0",
                    }
                    revert_balance_to_accept_account(
                        revert_balance_payload,
                        trn.from_user,
                        current_amount_plus_fess_and_vat,
                    )
        else:
            TIMEOUTS_UPDATE_LOGGER.debug(
                f"[Timeouts updates] [has no ref number ] update transaction {trn.uid} and ref {trn.reference_id} with failed status"
            )
            trn.status = "F"
            trn.from_user.root.budget.return_hold_balance(
                trn.amount, issuer_mapper[trn.issuer_type]
            )
            trn.save()
            total_failed = total_failed + 1
            if trn.from_accept == 'single':
                current_amount_plus_fess_and_vat = trn.from_user.root.budget.accumulate_amount_with_fees_and_vat(trn.amount, issuer_mapper[trn.issuer_type])
                revert_balance_payload = {
                    "transaction_id": trn.accept_balance_transfer_id,
                    "fees_amount_cents": "0",
                }
                revert_balance_to_accept_account(
                    revert_balance_payload,
                    trn.from_user,
                    current_amount_plus_fess_and_vat,
                )

    if email_notify:
        subject = f"Timeouts update from {start_date} To {end_date}"
        from_email = settings.SERVER_EMAIL
        message_body = f"total timeouts :{total_timeouts} total success: {total_success}, total failed: {total_failed}"
        TIMEOUTS_UPDATE_LOGGER.debug(
            f"[Timeouts updates] [send email for {email_notify}] total timeouts :{total_timeouts} total success: {total_success}, total failed: {total_failed}"
        )
        mail_to_be_sent = EmailMultiAlternatives(
            subject, message_body, from_email, [email_notify]
        )
        mail_to_be_sent.attach_alternative(message_body, "text/html")
        mail_to_be_sent.send()


@app.task()
def update_manual_batch_transactions_task(data):
    BankTransactionsChannel.update_manual_batch_transactions(data)


@app.task()
def self_update_bank_transactions_staging():
    start_date = timezone.now()
    end_date = timezone.now() - datetime.timedelta(int(16))

    latest_bank_trx_ids = (
        BankTransaction.objects.filter(Q(created_at__gte=end_date))
        .filter(Q(created_at__lte=start_date))
        .order_by("parent_transaction__transaction_id", "-id")
        .distinct("parent_transaction__transaction_id")
        .values_list("id", flat=True)
    )
    latest_bank_transactions = (
        BankTransaction.objects.filter(id__in=latest_bank_trx_ids)
        .filter(
            Q(status=AbstractBaseStatus.PENDING)
            | Q(status=AbstractBaseStatus.SUCCESSFUL)
        )
        .filter(~Q(transaction_status_code=8333))
        .order_by("created_at")
    )
    for trn in latest_bank_transactions:
        BankTransactionsChannel.update_bank_trx_status(
            trn,
            get_random_status(
                trn.get_last_updated_transaction().transaction_status_code
            ),
        )


def get_random_status(last_status_code):
    import random

    if last_status_code == "8000":
        return random.choice(
            [
                {
                    "TransactionStatusCode": "8111",
                    "TransactionStatusDescription": "Transaction received and validated successfully. Dispatched for being processed by the bank",
                },
                {
                    "TransactionStatusCode": "8111",
                    "TransactionStatusDescription": "Transaction received and validated successfully. Dispatched for being processed by the bank",
                },
                {
                    "TransactionStatusCode": "8111",
                    "TransactionStatusDescription": "Transaction received and validated successfully. Dispatched for being processed by the bank",
                },
                {
                    "TransactionStatusCode": "000005",
                    "TransactionStatusDescription": "Invalid Account Details",
                },
            ]
        )

    elif last_status_code == "8111":
        return {
            "TransactionStatusCode": "8222",
            "TransactionStatusDescription": "Successful with warning, A transfer will take place once authorized by the receiver bank",
        }

    else:
        return random.choice(
            [
                {
                    "TransactionStatusCode": "8333",
                    "TransactionStatusDescription": "Successful, transaction is settled by the receiver bank",
                },
                {
                    "TransactionStatusCode": "8333",
                    "TransactionStatusDescription": "Successful, transaction is settled by the receiver bank",
                },
                {
                    "TransactionStatusCode": "8333",
                    "TransactionStatusDescription": "Successful, transaction is settled by the receiver bank",
                },
                {
                    "TransactionStatusCode": "000100",
                    "TransactionStatusDescription": "Incorrect Account Number",
                },
            ]
        )


@app.task()
def disburse_accept_pending_transactions():
    from django.utils.timezone import datetime, make_aware, timedelta
    from disbursement.models import VMTData
    import copy
    from utilities.logging import logging_message

    INSTANT_CASHIN_SUCCESS_LOGGER = logging.getLogger("instant_cashin_success")
    INSTANT_CASHIN_FAILURE_LOGGER = logging.getLogger("instant_cashin_failure")
    INSTANT_CASHIN_REQUEST_LOGGER = logging.getLogger("instant_cashin_requests")

    from payouts.settings import TIMEOUT_CONSTANTS
    from rest_framework.exceptions import ValidationError
    from rest_framework import status
    from django.core.exceptions import ImproperlyConfigured
    from django.utils.translation import gettext as _

    INTERNAL_ERROR_MSG = _(
        "Process stopped during an internal error, can you try again or contact your support team"
    )
    EXTERNAL_ERROR_MSG = _(
        "Process stopped during an external error, can you try again or contact your support team"
    )
    TIMEOUT_ERROR_MSG = _("Request timeout error")
    issuer_mapper = {
        "V": "vodafone",
        "E": "etisalat",
        "O": "orange",
        "B": "bank_wallet",
    }

    trns = InstantTransaction.objects.filter(from_accept="single", status="P")
    for trn in trns:
        trn.disbursed_date = datetime.now()
        if make_aware(datetime.now()) - trn.created_at > timedelta(hours=1):
            instant_user = trn.from_user
            current_amount_plus_fess_and_vat = (
                instant_user.root.budget.accumulate_amount_with_fees_and_vat(
                    trn.amount, issuer_mapper[trn.issuer_type]
                )
            )
            revert_balance_payload = {
                "transaction_id": trn.accept_balance_transfer_id,
                "fees_amount_cents": "0",
            }
            vmt_data = VMTData.objects.get(vmt=instant_user.root.client.creator)
            data_dict = vmt_data.return_vmt_data(VMTData.INSTANT_DISBURSEMENT)
            data_dict["MSISDN2"] = trn.anon_recipient
            data_dict["AMOUNT"] = str(trn.amount)
            data_dict["WALLETISSUER"] = "VODAFONE"
            data_dict["MSISDN"] = trn.anon_sender
            data_dict["PIN"] = get_from_env(
                f"{instant_user.root.super_admin.username}_VODAFONE_PIN"
            )
            data_dict["EXTREFNUM"] = str(trn.uid)
            if issuer_mapper[trn.issuer_type] in ["orange", "etisalat", "bank_wallet"]:
                data_dict["TYPE"] = "DPSTREQ"
            request_data_dictionary_without_pins = copy.deepcopy(data_dict)
            request_data_dictionary_without_pins["PIN"] = "xxxxxx"
            INSTANT_CASHIN_REQUEST_LOGGER.debug(
                f"[request] [DATA DICT TO CENTRAL]"
                f"CELERY TASK"
                f"{request_data_dictionary_without_pins}"
            )
            if data_dict["MSISDN2"] == get_from_env(
                f"test_number_for_{issuer_mapper[trn.issuer_type]}"
            ) and get_from_env("ENVIRONMENT") in ["staging", "local"]:
                trn.mark_successful(
                    200,
                    f"amount {str(trn.amount)} is disbursed successfully",
                )
                # release hold balance
                instant_user.root.budget.release_hold_balance(
                    trn.amount, issuer_mapper[trn.issuer_type]
                )
                trn.save()
            else:
                try:
                    trx_response = requests.post(
                        get_from_env(vmt_data.vmt_environment),
                        json=data_dict,
                        verify=False,
                        timeout=TIMEOUT_CONSTANTS["CENTRAL_UIG"],
                    )
                    if trx_response.ok:
                        json_trx_response = trx_response.json()
                        trn.reference_id = json_trx_response["TXNID"]
                    else:
                        raise ImproperlyConfigured(trx_response.text)
                    if json_trx_response["TXNSTATUS"] == "200":
                        INSTANT_CASHIN_SUCCESS_LOGGER.debug(
                            f"[response] [SUCCESSFUL TRX]"
                            f"CELERY TASK"
                            f"{json_trx_response}"
                        )
                        trn.mark_successful(
                            json_trx_response["TXNSTATUS"], json_trx_response["MESSAGE"]
                        )
                        # release hold balance
                        instant_user.root.budget.release_hold_balance(
                            trn.amount, issuer_mapper[trn.issuer_type]
                        )
                        trn.save()

                    elif (
                        json_trx_response["TXNSTATUS"] == "501"
                        or json_trx_response["TXNSTATUS"] == "6005"
                    ):
                        INSTANT_CASHIN_FAILURE_LOGGER.debug(
                            f"[response] [FAILED TRX]"
                            f"CELERY TASK"
                            f"timeout, {json_trx_response}"
                        )
                        trn.mark_unknown(
                            json_trx_response["TXNSTATUS"], json_trx_response["MESSAGE"]
                        )
                        trn.save()
                    else:
                        INSTANT_CASHIN_FAILURE_LOGGER.debug(
                            f"[response] [FAILED TRX]"
                            f"CELERY TASK"
                            f"{json_trx_response}"
                        )
                        trn.mark_failed(
                            json_trx_response["TXNSTATUS"], json_trx_response["MESSAGE"]
                        )
                        # return hold balance
                        instant_user.root.budget.return_hold_balance(
                            trn.amount, issuer_mapper[trn.issuer_type]
                        )
                        revert_balance_to_accept_account(
                            revert_balance_payload,
                            trn.from_user,
                            current_amount_plus_fess_and_vat,
                        )
                        trn.save()

                except ValidationError as e:
                    INSTANT_CASHIN_FAILURE_LOGGER.debug(
                        f"[message] [DISBURSEMENT VALIDATION ERROR]"
                        f"CELERY TASK"
                        f"{e.args}"
                    )

                    trn.mark_failed(
                        status.HTTP_500_INTERNAL_SERVER_ERROR, INTERNAL_ERROR_MSG
                    )
                    # return hold balance
                    instant_user.root.budget.return_hold_balance(
                        trn.amount, issuer_mapper[trn.issuer_type]
                    )
                    revert_balance_to_accept_account(
                        revert_balance_payload,
                        trn.from_user,
                        current_amount_plus_fess_and_vat,
                    )
                    trn.save()

                except (requests.Timeout, TimeoutError) as e:
                    INSTANT_CASHIN_FAILURE_LOGGER.debug(
                        f"[response] [ERROR FROM CENTRAL]"
                        f"CELERY TASK"
                        f"timeout, {e.args}"
                    )
                    trn.mark_unknown(status.HTTP_408_REQUEST_TIMEOUT, TIMEOUT_ERROR_MSG)
                    trn.save()

                except (ImproperlyConfigured, Exception) as e:
                    INSTANT_CASHIN_FAILURE_LOGGER.debug(
                        f"[response] [ERROR FROM CENTRAL]"
                        f"CELERY TASK"
                        f"{e.args}"
                    )
                    trn.mark_failed(
                        status.HTTP_424_FAILED_DEPENDENCY, EXTERNAL_ERROR_MSG
                    )
                    # return hold balance
                    instant_user.root.budget.return_hold_balance(
                        trn.amount, issuer_mapper[trn.issuer_type]
                    )


def revert_balance_to_accept_account(payload, user, current_fees_and_vat):
    ACCEPT_BALANCE_TRANSFER_LOGGER = logging.getLogger("accept_balance_transfer")
    url = get_from_env("DECLINE_SINGLE_STEP_URL")
    headers = {"Authorization": get_from_env("SINGLE_STEP_TOKEN")}
    ACCEPT_BALANCE_TRANSFER_LOGGER.debug(f"[request] [revert balance] -- {payload} ")
    revert_response = requests.post(url, json=payload, headers=headers)
    json_response = revert_response.json()
    ACCEPT_BALANCE_TRANSFER_LOGGER.debug(
        f"[response] [revert balance] -- {json_response} "
    )
    if json_response.get("success"):
        user.root.budget.current_balance -= current_fees_and_vat
        user.root.budget.save()
