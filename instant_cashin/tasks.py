# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext as _

from data.decorators import respects_language
from data.utils import deliver_mail
from payouts.settings.celery import app
from users.models import User

from .resources import PendingOrangeInstantTransactionsModelResource


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
