# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.db.models import F, Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext as _

from data.decorators import respects_language
from data.utils import deliver_mail_to_multiple_recipients_with_attachment
from disbursement.models import DisbursementData
from instant_cashin.utils import get_from_env
from payouts.settings.celery import app
from users.models import EntitySetup, User

from .functions import render_to_pdf
from .models import AbstractBaseDocStatus, Budget

BUDGET_LOGGER = logging.getLogger("custom_budgets")


def retrieve_onboarded_entities_and_disbursement_records_over_week(superadmin_username):
    """Retrieve the newly onboarded entities and the disbursement trx over the last week for superadmin"""

    records_result = []
    one_week_ago = timezone.now() - timedelta(days=7)
    entities_setup = EntitySetup.objects.filter(user__username=superadmin_username)

    for entity_setup in entities_setup:
        trx_records = (
            DisbursementData.objects.filter(
                doc__owner__hierarchy=entity_setup.entity.hierarchy
            )
            .filter(created_at__gte=one_week_ago)
            .filter(
                doc__disbursement_txn__doc_status=AbstractBaseDocStatus.DISBURSED_SUCCESSFULLY
            )
            .filter(reason='SUCCESS')
            .values('amount')
        )
        trx_count = trx_records.count()
        trx_total_amount = (
            sum([trx['amount'] for trx in trx_records]) if trx_count > 0 else 0.0
        )
        records_result.append(
            {
                'admin': entity_setup.entity.username,
                'count': trx_count,
                'amount': trx_total_amount,
            }
        )

    last_week_users = (
        entities_setup.filter(entity__date_joined__gte=one_week_ago)
        .values('entity__username', 'entity__email', 'entity__mobile_no')
        .order_by('-entity__date_joined')
    )
    return {
        'onboarded_entities': last_week_users,
        'onboarded_entities_count': last_week_users.count(),
        'records_result': records_result,
    }


def generate_pdf_report(context={}):
    """Generate pdf report based on the given context data"""

    pdf = render_to_pdf('utilities/new_entities_report.html', context_dict=context)
    filename = f'weekly_report_{timezone.now().strftime("%Y_%m_%d_%H_%M_%S")}.pdf'
    filepath = f"{settings.MEDIA_ROOT}/documents/weekly_reports/{filename}"
    content = f"attachment; filename={filename}"
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = content

    with open(filepath, "wb") as f:
        f.write(response.content)

    return filepath


@app.task()
@respects_language
def generate_onboarded_entities_report(recipients_list, superadmin_username, **kwargs):
    """Generate report of the newly onboarded entities per week"""

    context = retrieve_onboarded_entities_and_disbursement_records_over_week(
        superadmin_username
    )
    filepath = generate_pdf_report(context)
    GENERATE_REPORT = logging.getLogger('generate_sheet')
    GENERATE_REPORT.debug(
        f"[message] [WEEKLY REPORT GENERATED SUCCESSFULLY] [anonymous] -- "
        f"Superadmin: {superadmin_username}, recipients: {recipients_list}, Report: {filepath}"
    )

    sender = settings.SERVER_EMAIL
    subject = _('Payouts Weekly Report')
    message = _(
        'Dear Team,\n\nKindly find the weekly report attached.\n\nBest Regards,'
    )
    mail = EmailMessage(subject, message, sender, recipients_list)
    mail.attach_file(filepath)
    return mail.send()


@app.task()
@respects_language
def send_transfer_request_email(
    admin_username, message, attachment_file_name=None, automatic=False, **kwargs
):
    """"""
    # 1. Prepare recipients list
    business_team = [
        dict(email=email)
        for email in get_from_env('BUSINESS_TEAM_EMAILS_LIST').split(',')
    ]

    # 2. Get admin user object
    admin_user = User.objects.get(username=admin_username)

    subject = "Automatic " if automatic else ""
    # 3. Send the email
    if attachment_file_name:
        file = default_storage.open(attachment_file_name)
        deliver_mail_to_multiple_recipients_with_attachment(
            admin_user,
            _(f" {subject}Transfer Request By User {admin_username}"),
            message,
            business_team,
            file,
        )
    else:
        deliver_mail_to_multiple_recipients_with_attachment(
            admin_user,
            _(f" {subject}Transfer Request By User {admin_username}"),
            message,
            business_team,
        )

    BUDGET_LOGGER.debug(
        f"[message] [transfer request Email] from :- [{admin_username}]  to:- {business_team}"
    )
    return True


@app.task()
@respects_language
def check_disk_space_and_send_warning_email():
    import shutil

    # get total space and used space and free space
    total, used, free = shutil.disk_usage("/")

    # send email if free space <= 3 GiB
    if (free // (2**30)) <= 3:
        developers_team = [admin[1] for admin in settings.ADMINS]
        subject = f'Warning, Payout {get_from_env("ENVIRONMENT").capitalize()} Server Run Out Of Disk Space'
        message_body = (
            """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
                <html xmlns="http://www.w3.org/1999/xhtml">
                <head>
                    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
                    <link rel="icon" sizes="" href="https://yt3.ggpht.com/a-/AN66SAzzGZByUtn6CpHHJVIEOuqQbvAqwgPiKy1RTw=s900-mo-c-c0xffffffff-rj-k-no" type="image/jpg" />
                    <title>SolarWinds Orion Email Alert Template</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                        <style>
                            body {
                                background-color: #f0f0f0;
                                font-family: Arial, sans-serif;
                                color: #000000;
                            }
                            .center {
                                text-align: center;
                            }
                            td {
                                padding: 20px 50px 30px 50px;
                            }
                            td.notification {
                                padding: 10px 50px 30px 50px;
                            }
                            h1,h2 {
                                font-size: 22px;
                                color: #000000;
                                font-weight: normal;
                            }
                            p {
                                font-size: 15px;
                                color: #000000;
                            }
                            .notification h1 {
                                font-size: 26px;
                                color: #000000;
                                font-weight: normal;
                            }
                            .notification p {
                                font-size: 18px;
                            }
                            .warning {
                                border-top: 20px #c08040 solid;
                                background-color: #e0c4aa;
                            }
                            .warning p {
                                color: #000000;
                            }
                            .content {
                                width: 600px;
                            }
                            @media only screen and (max-width: 600px) {
                                .content {
                                    width: 100%;
                                }
                            }
                            @media only screen and (max-width: 400px) {
                                td {
                                    padding: 15px 25px;
                                }
                                h1{
                                    font-size: 20px;
                                }
                                p {
                                    font-size: 13px;
                                }
                                td.notification {
                                    text-align: center;
                                    padding: 10px 25px 15px 25px;
                                }
                                .notification h1 {
                                    font-size: 22px;
                                }
                                    .notification p {
                                    font-size: 16px;
                                }
                            }
                    </style>
                </head>"""
            + f"""
                <body style="margin: 0; padding: 0">
                    <table style="border: none" cellpadding="0" cellspacing="0" width="100%">
                        <tr>
                            <td style="padding: 15px 0">
                                <table style="border: none; margin-left: auto; margin-right: auto" cellpadding="0" cellspacing="0" width="600" class="content">
                                    <tr>
                                        <td class="warning notification">
                                            <h1>Warning</h1>
                                            <h2>Payout Server Run Out Of Disk Space</h2>
                                            <h4>Payout Server Disk Size Information :-</h4>
                                            <p>Total:  <b>{(total // (2**30))} GiB</b></p>
                                            <p>Used:  <b>{(used // (2**30))} GiB</b></p>
                                            <p>Free:  <b>{(free // (2**30))} GiB</b></p>
                                            <p><b>Please remove old logs to free up some space.</b></p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </body>
                </html>
            """
        )
        from_email = settings.SERVER_EMAIL
        mail_to_be_sent = EmailMultiAlternatives(
            subject, message_body, from_email, developers_team
        )
        mail_to_be_sent.attach_alternative(message_body, "text/html")

        return mail_to_be_sent.send()


@app.task()
@respects_language
def notify_clients_with_email_that_balance_under_limit():
    """
    celery task to run every day to check if merchant balance under
    his limit and if yes notify him by email
    """

    budgets_with_balance_under_limit = Budget.objects.filter(
        ~Q(merchant_limit=None),
        ~Q(merchant_limit=Decimal('0.0')),
        Q(merchant_limit__lte=F('current_balance')),
    )

    subject = "[Payouts] Unplanned Outage Notification"
    from_email = settings.SERVER_EMAIL

    body = """"""

    for current_budget in budgets_with_balance_under_limit:
        mail_to_be_sent = EmailMultiAlternatives(
            subject, body, from_email, [current_budget.disburser.email]
        )
        mail_to_be_sent.attach_alternative(body, "text/html")
        mail_to_be_sent.send()
