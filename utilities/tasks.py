# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import timedelta
import logging

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
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
from .models import AbstractBaseDocStatus

BUDGET_LOGGER = logging.getLogger("custom_budgets")


def retrieve_onboarded_entities_and_disbursement_records_over_week(superadmin_username):
    """Retrieve the newly onboarded entities and the disbursement trx over the last week for superadmin"""

    records_result = []
    one_week_ago = timezone.now() - timedelta(days=7)
    entities_setup = EntitySetup.objects.filter(user__username=superadmin_username)

    for entity_setup in entities_setup:
        trx_records = DisbursementData.objects.filter(doc__owner__hierarchy=entity_setup.entity.hierarchy).\
            filter(created_at__gte=one_week_ago).\
            filter(doc__disbursement_txn__doc_status=AbstractBaseDocStatus.DISBURSED_SUCCESSFULLY).\
            filter(reason='SUCCESS').values('amount')
        trx_count = trx_records.count()
        trx_total_amount = sum([trx['amount'] for trx in trx_records]) if trx_count > 0 else 0.0
        records_result.append({'admin': entity_setup.entity.username, 'count': trx_count, 'amount': trx_total_amount})

    last_week_users = entities_setup.filter(entity__date_joined__gte=one_week_ago).\
        values('entity__username', 'entity__email', 'entity__mobile_no').order_by('-entity__date_joined')
    return {
        'onboarded_entities': last_week_users,
        'onboarded_entities_count': last_week_users.count(),
        'records_result': records_result
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

    context =  retrieve_onboarded_entities_and_disbursement_records_over_week(superadmin_username)
    filepath = generate_pdf_report(context)
    GENERATE_REPORT = logging.getLogger('generate_sheet')
    GENERATE_REPORT.debug(f"[message] [WEEKLY REPORT GENERATED SUCCESSFULLY] [anonymous] -- "
                          f"Superadmin: {superadmin_username}, recipients: {recipients_list}, Report: {filepath}")

    sender = settings.SERVER_EMAIL
    subject = _('Payouts Weekly Report')
    message = _('Dear Team,\n\nKindly find the weekly report attached.\n\nBest Regards,')
    mail = EmailMessage(subject, message, sender, recipients_list)
    mail.attach_file(filepath)
    return mail.send()


@app.task()
@respects_language
def send_transfer_request_email(admin_username, message, attachment_file_name=None, **kwargs):
    """"""
    # 1. Prepare recipients list
    business_team = [dict(email=email) for email in get_from_env('BUSINESS_TEAM_EMAILS_LIST').split(',')]

    # 2. Get admin user object
    admin_user = User.objects.get(username=admin_username)

    # 3. Send the email
    if attachment_file_name:
        file = default_storage.open(attachment_file_name)
        deliver_mail_to_multiple_recipients_with_attachment(
                admin_user, _(f" Transfer Request By User {admin_username}"), message, business_team, file
        )
    else:
        deliver_mail_to_multiple_recipients_with_attachment(
                admin_user, _(f" Transfer Request By User {admin_username}"), message, business_team
        )

    BUDGET_LOGGER.debug(
            f"[message] [transfer request Email] from :- [{admin_username}]  to:- {business_team}"
    )
    return True
