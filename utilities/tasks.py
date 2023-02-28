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
        Q(merchant_limit__gt=F('current_balance')),
    )

    subject = "[Payouts] Minimum Balance Notification"
    from_email = settings.SERVER_EMAIL

    body = """<!doctype html><html><head><meta name="viewport" content="width=device-width" />
                <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
                <title>System Notification</title>
                <style>
                  img {
                    border: none;
                    -ms-interpolation-mode: bicubic;
                    max-width: 100%;
                  }
                  body {
                    background-color: #f6f6f6;
                    font-family: sans-serif;
                    -webkit-font-smoothing: antialiased;
                    font-size: 14px;
                    line-height: 1.4;
                    margin: 0;
                    padding: 0;
                    -ms-text-size-adjust: 100%;
                    -webkit-text-size-adjust: 100%;
                  }
                  table {
                    border-collapse: separate;
                    mso-table-lspace: 0pt;
                    mso-table-rspace: 0pt;
                    width: 100%; }
                    table td {
                      font-family: sans-serif;
                      font-size: 14px;
                      vertical-align: top;
                  }
                  .body {
                    background-color: #f6f6f6;
                    width: 100%;
                  }
                  .container {
                    display: block;
                    margin: 0 auto !important;
                    /* makes it centered */
                    max-width: 580px;
                    padding: 10px;
                    width: 580px;
                  }
                  .content {
                    box-sizing: border-box;
                    display: block;
                    margin: 0 auto;
                    max-width: 580px;
                    padding: 10px;
                  }
                  .main {
                    background: #ffffff;
                    border-radius: 3px;
                    width: 100%;
                  }
                  .wrapper {
                    box-sizing: border-box;
                    padding: 20px;
                  }
                  .content-block {
                    padding-bottom: 10px;
                    padding-top: 10px;
                  }
                  .footer {
                    clear: both;
                    margin-top: 10px;
                    text-align: center;
                    width: 100%;
                  }
                    .footer td,
                    .footer p,
                    .footer span,
                    .footer a {
                      color: #999999;
                      font-size: 12px;
                      text-align: center;
                  }
                  h1,
                  h2,
                  h3,
                  h4 {
                    color: #000000;
                    font-family: sans-serif;
                    font-weight: 400;
                    line-height: 1.4;
                    margin: 0;
                    margin-bottom: 30px;
                  }

                  h1 {
                    font-size: 35px;
                    font-weight: 300;
                    text-align: center;
                    text-transform: capitalize;
                  }
                  p,
                  ul,
                  ol {
                    font-family: sans-serif;
                    font-size: 14px;
                    font-weight: normal;
                    margin: 0;
                    margin-bottom: 15px;
                  }
                  p li,
                  ul li,
                  ol li {
                      list-style-position: inside;
                      margin-left: 5px;
                  }
                  a {
                    color: #3498db;
                    text-decoration: underline;
                  }
                  .btn {
                    box-sizing: border-box;
                    width: 100%; }
                    .btn > tbody > tr > td {
                      padding-bottom: 15px; }
                    .btn table {
                      width: auto;
                  }
                    .btn table td {
                      background-color: #ffffff;
                      border-radius: 5px;
                      text-align: center;
                  }
                    .btn a {
                      background-color: #ffffff;
                      border: solid 1px #3498db;
                      border-radius: 5px;
                      box-sizing: border-box;
                      color: #3498db;
                      cursor: pointer;
                      display: inline-block;
                      font-size: 14px;
                      font-weight: bold;
                      margin: 0;
                      padding: 12px 25px;
                      text-decoration: none;
                      text-transform: capitalize;
                  }

                  .btn-primary table td {
                    background-color: #3498db;
                  }
                  .btn-primary a {
                    background-color: #3498db;
                    border-color: #3498db;
                    color: #ffffff;
                  }
                  .last {
                    margin-bottom: 0;
                  }

                  .first {
                    margin-top: 0;
                  }

                  .align-center {
                    text-align: center;
                  }

                  .align-right {
                    text-align: right;
                  }

                  .align-left {
                    text-align: left;
                  }

                  .clear {
                    clear: both;
                  }

                  .mt0 {
                    margin-top: 0;
                  }

                  .mb0 {
                    margin-bottom: 0;
                  }

                  .preheader {
                    color: transparent;
                    display: none;
                    height: 0;
                    max-height: 0;
                    max-width: 0;
                    opacity: 0;
                    overflow: hidden;
                    mso-hide: all;
                    visibility: hidden;
                    width: 0;
                  }

                  .powered-by a {
                    text-decoration: none;
                  }

                  hr {
                    border: 0;
                    border-bottom: 1px solid #f6f6f6;
                    margin: 20px 0;
                  }
                  @media only screen and (max-width: 620px) {
                    table[class=body] h1 {
                      font-size: 28px !important;
                      margin-bottom: 10px !important;
                    }
                    table[class=body] p,
                    table[class=body] ul,
                    table[class=body] ol,
                    table[class=body] td,
                    table[class=body] span,
                    table[class=body] a {
                      font-size: 16px !important;
                    }
                    table[class=body] .wrapper,
                    table[class=body] .article {
                      padding: 10px !important;
                    }
                    table[class=body] .content {
                      padding: 0 !important;
                    }
                    table[class=body] .container {
                      padding: 0 !important;
                      width: 100% !important;
                    }
                    table[class=body] .main {
                      border-left-width: 0 !important;
                      border-radius: 0 !important;
                      border-right-width: 0 !important;
                    }
                    table[class=body] .btn table {
                      width: 100% !important;
                    }
                    table[class=body] .btn a {
                      width: 100% !important;
                    }
                    table[class=body] .img-responsive {
                      height: auto !important;
                      max-width: 100% !important;
                      width: auto !important;
                    }
                  }
                  @media all {
                    .ExternalClass {
                      width: 100%;
                    }
                    .ExternalClass,
                    .ExternalClass p,
                    .ExternalClass span,
                    .ExternalClass font,
                    .ExternalClass td,
                    .ExternalClass div {
                      line-height: 100%;
                    }
                    .apple-link a {
                      color: inherit !important;
                      font-family: inherit !important;
                      font-size: inherit !important;
                      font-weight: inherit !important;
                      line-height: inherit !important;
                      text-decoration: none !important;
                    }
                    #MessageViewBody a {
                      color: inherit;
                      text-decoration: none;
                      font-size: inherit;
                      font-family: inherit;
                      font-weight: inherit;
                      line-height: inherit;
                    }
                    .btn-primary table td:hover {
                      background-color: #34495e !important;
                    }
                    .btn-primary a:hover {
                      background-color: #34495e !important;
                      border-color: #34495e !important;
                    }
                  }
                </style></head><body class="">
                <span class="preheader">System Notification</span>
                <table role="presentation" border="0" cellpadding="0" cellspacing="0" class="body">
                  <tr><td>&nbsp;</td>
                    <td class="container">
                      <div class="content">
                        <table role="presentation" class="main">
                          <tr>
                            <td class="wrapper">
                              <table role="presentation" border="0" cellpadding="0" cellspacing="0">
                                <tr>
                                  <td>
                                    <p>Dear """
    body_middle = """,</p><p>Kindly note that you have reached the minimum balance """
    body_last = """. Please top up your account to keep your operations running.</p>
                                    <p>Regards,</p>
                                    <p>Payouts Support team.</p>
                                  </td>
                                </tr>
                              </table>
                            </td>
                          </tr>
                        </table>
                      </div>
                    </td>
                    <td>&nbsp;</td>
                  </tr>
                </table>
              </body></html>"""

    for current_budget in budgets_with_balance_under_limit:
        message = (
            body
            + str(current_budget.disburser.username)
            + body_middle
            + str(current_budget.merchant_limit)
            + body_last
        )
        mail_to_be_sent = EmailMultiAlternatives(
            subject, message, from_email, [current_budget.disburser.email]
        )
        mail_to_be_sent.attach_alternative(body, "text/html")
        mail_to_be_sent.send()
