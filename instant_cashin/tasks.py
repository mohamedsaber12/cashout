# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import logging

from django.db.models import Q
from django.utils import timezone

from core.models import AbstractBaseStatus
from data.decorators import respects_language
from disbursement.models import BankTransaction
from payouts.settings.celery import app

from .specific_issuers_integrations import BankTransactionsChannel
from instant_cashin.api.serializers import BankTransactionResponseModelSerializer
import requests
import json
from instant_cashin.specific_issuers_integrations.aman.instant_cashin import UUIDEncoder

ACH_GET_TRX_STATUS_LOGGER = logging.getLogger("ach_get_transaction_status")


@app.task()
@respects_language
def check_for_status_updates_for_latest_bank_transactions(days_delta=10, **kwargs):
    """Task for updating pending bank transactions from EBC for the last 5 days at max"""
    try:
        five_days_ago = timezone.now() - datetime.timedelta(int(days_delta))
        latest_bank_trx_ids = BankTransaction.objects.\
            filter(created_at__gte=five_days_ago).\
            order_by("parent_transaction__transaction_id", "-id").distinct("parent_transaction__transaction_id").\
            values_list("id", flat=True)
        latest_bank_transactions = BankTransaction.objects.\
            filter(id__in=latest_bank_trx_ids).\
            filter(Q(status=AbstractBaseStatus.PENDING) | Q(status=AbstractBaseStatus.SUCCESSFUL)).\
            order_by("created_at")

        if latest_bank_transactions.count() > 0:

            ACH_GET_TRX_STATUS_LOGGER.debug(
                    f"[message] [check for trx update task] [celery_task] -- "
                    f"transactions count: {latest_bank_transactions.count()}, "
                    f"{[trx for trx in latest_bank_transactions]}"
            )

            for bank_trx in latest_bank_transactions:
                BankTransactionsChannel.get_transaction_status(bank_trx)
                
                # send bank transaction callback notifications 
                if bank_trx.user_created.root.root.callback_url:
                    callback_url = bank_trx.user_created.root.root.callback_url
                    transaction = BankTransaction.objects.filter(~Q(creditor_bank__in=["THWL", "MIDG"])).\
                        filter(Q(parent_transaction=bank_trx)).\
                            order_by("parent_transaction__transaction_id", "-id").distinct("parent_transaction__transaction_id")
                    req_body = BankTransactionResponseModelSerializer(transaction.first())
                    requests.post(callback_url, data=json.dumps(req_body.data, cls=UUIDEncoder))


        return True
    except (BankTransaction.DoesNotExist, ValueError, Exception) as e:
        # ToDo: Add logging
        return False
