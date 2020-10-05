# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from core.models import AbstractBaseStatus
from data.decorators import respects_language
from data.utils import deliver_mail
from disbursement.models import BankTransaction
from payouts.settings.celery import app
from users.models import User

from .resources import PendingOrangeInstantTransactionsModelResource
from .specific_issuers_integrations import BankTransactionsChannel


@app.task()
@respects_language
def generate_pending_orange_instant_transactions(username, raw_date, **kwargs):
    """
    Generates csv sheet of all the pending Orange instant transactions which occurred at the provided raw date
    """
    user = User.objects.get(username=username)
    suffix = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = _(f"173_{username}_{suffix}.csv")
    file_path = f"{settings.MEDIA_ROOT}/documents/instant_transactions/{filename}"
    download_url = settings.BASE_URL + str(reverse('instant_cashin:serve_download')) + f"?filename={filename}"

    dataset = PendingOrangeInstantTransactionsModelResource(user, raw_date)
    dataset = dataset.export()

    with open(file_path, "w") as f:
        f.write(dataset.csv)

    message = _(
            f"Dear <strong>{str(username).capitalize()}</strong><br><br>You can download " +
            f"the pending Orange transactions occurred at {raw_date}.<br>" +
            f"<a href='{download_url}' >Download</a> from here.<br><br>Thanks, BR"
    )
    deliver_mail(user, _(f' Pending Orange Transactions at {raw_date} - File Download'), message)


@app.task()
@respects_language
def check_for_status_updates_for_pending_bank_transactions(days_delta=5, **kwargs):
    """Task for updating pending bank transactions from EBC for the last 5 days at max"""
    try:
        five_days_ago = timezone.now() - datetime.timedelta(int(days_delta))
        pending_bank_transactions = BankTransaction.objects.\
            filter(status=AbstractBaseStatus.PENDING).\
            filter(created_at__gte=five_days_ago).\
            order_by("parent_transaction__transaction_id", "-id").distinct("parent_transaction__transaction_id")

        # ToDo: Add logging

        if pending_bank_transactions.count() > 0:
            for bank_trx in pending_bank_transactions:
                BankTransactionsChannel.get_transaction_status(bank_trx)

        return True
    except (BankTransaction.DoesNotExist, ValueError, Exception) as e:
        # ToDo: Add logging
        return False
