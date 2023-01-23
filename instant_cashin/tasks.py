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
        transaction_status_code__in=[6005, 501],
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
                    balance_before = trn.from_user.root.budget.get_current_balance()
                    balance_after = trn.from_user.root.budget.update_disbursed_amount_and_current_balance(
                        trn.amount, issuer_mapper[trn.issuer_type]
                    )
                    trn.balance_before = balance_before
                    trn.balance_after = balance_after
                    trn.save()
                    total_success = total_success + 1
                else:
                    TIMEOUTS_UPDATE_LOGGER.debug(
                        f"[Timeouts updates] [found on report ] update transaction {trn.uid} and ref {trn.reference_id} with failed status"
                    )
                    trn.status = "F"
                    trn.save()
                    total_failed = total_failed + 1
            else:
                TIMEOUTS_UPDATE_LOGGER.debug(
                    f"[Timeouts updates] [not found on report ] update transaction {trn.uid} and ref {trn.reference_id} with failed status"
                )
                trn.status = "F"
                trn.save()
                total_failed = total_failed + 1
        else:
            TIMEOUTS_UPDATE_LOGGER.debug(
                f"[Timeouts updates] [has no ref number ] update transaction {trn.uid} and ref {trn.reference_id} with failed status"
            )
            trn.status = "F"
            trn.save()
            total_failed = total_failed + 1

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
