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
from payouts.settings.celery import app

from .specific_issuers_integrations import BankTransactionsChannel
import requests
from celery.task import control
from instant_cashin.utils import get_from_env

ACH_GET_TRX_STATUS_LOGGER = logging.getLogger("ach_get_transaction_status")


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
                f"[message] [check for EBC status] [celery_task] -- "
                f"Exeption: {e}"
            )
            return False
        # check if there's same task is running
        active_tasks = control.inspect().active()
        ach_worker = get_from_env("ach_worker")
        ACH_GET_TRX_STATUS_LOGGER.debug(
                f"Active Tasks {active_tasks.get(ach_worker)}"
            )
        num_of_current_tasks = 0
        for tsk in active_tasks.get(ach_worker):
            if tsk["type"] == 'instant_cashin.tasks.check_for_status_updates_for_latest_bank_transactions':
                num_of_current_tasks += 1
            if tsk["type"] == 'instant_cashin.tasks.check_for_status_updates_for_latest_bank_transactions_more_than_6_days':
                return False
        if num_of_current_tasks > 1:
            return False
    

    try:
        five_days_ago = timezone.now() - datetime.timedelta(int(days_delta))
        latest_bank_trx_ids = BankTransaction.objects.\
            filter(Q(created_at__gte=five_days_ago)).\
            order_by("parent_transaction__transaction_id", "-id").distinct("parent_transaction__transaction_id").\
            values_list("id", flat=True)
        latest_bank_transactions = BankTransaction.objects.\
            filter(id__in=latest_bank_trx_ids).\
            filter(Q(status=AbstractBaseStatus.PENDING) | Q(status=AbstractBaseStatus.SUCCESSFUL)).\
            filter(~Q(transaction_status_code=8333)).\
            order_by("created_at")

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
                f"check for EBC status Error {e}"
            )
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
        ACH_GET_TRX_STATUS_LOGGER.debug(
                f"Active Tasks {active_tasks.get(ach_worker)}"
            )
        num_of_current_tasks = 0
        for tsk in active_tasks.get(ach_worker):
            if tsk["type"] == 'instant_cashin.tasks.check_for_status_updates_for_latest_bank_transactions_more_than_6_days':
                num_of_current_tasks += 1
            if tsk["type"] == 'instant_cashin.tasks.check_for_status_updates_for_latest_bank_transactions':
                return False
        if num_of_current_tasks > 1:
            return False
    try:
        start_date = timezone.now()
        end_date = timezone.now() - datetime.timedelta(int(16))
        latest_bank_trx_ids = BankTransaction.objects.\
            filter(Q(created_at__gte=end_date)).\
            filter(Q(created_at__lte=start_date)).\
            order_by("parent_transaction__transaction_id", "-id").distinct("parent_transaction__transaction_id").\
            values_list("id", flat=True)
        latest_bank_transactions = BankTransaction.objects.\
            filter(id__in=latest_bank_trx_ids).\
            filter(Q(status=AbstractBaseStatus.PENDING) | Q(status=AbstractBaseStatus.SUCCESSFUL)).\
            filter(~Q(transaction_status_code=8333)).\
            order_by("created_at")

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
