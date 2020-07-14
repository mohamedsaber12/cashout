# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.utils.translation import gettext as _

from data.decorators import respects_language
from payouts.settings.celery import app
from users.models import RootUser


@app.task()
@respects_language
def generate_onboarded_entities_report(recipients_list, **kwargs):
    """Generate report of the newly onboarded entities per week"""

    one_week_ago = timezone.now() - timedelta(days=7)
    last_week_users = RootUser.objects.filter(date_joined__gte=one_week_ago).values('username', 'email', 'mobile_no')
    last_week_users_count = last_week_users.count()
    message = f'Total newly on-boarded entities over the last week: {last_week_users_count} entity(ies)<br><br>'
    for user in list(last_week_users):
        message += f"<strong>Username:</strong> {user['username']}<br>"
        message += f"<strong>Email:</strong> {user['email']}<br>"
        message += f"<strong>Mobile Number:</strong> {user['mobile_no']}<br><br>"
    message += "Best Regards,"

    from_email = settings.SERVER_EMAIL
    mail_subject = _('On-boarded Entities Weekly Report')
    mail_to_be_sent = EmailMultiAlternatives(mail_subject, message, from_email, recipients_list)
    mail_to_be_sent.attach_alternative(message, "text/html")
    return mail_to_be_sent.send()
