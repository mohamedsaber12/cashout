# -*- coding: UTF-8 -*-
from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import gettext as _
from payouts.settings.celery import app
from users.models import RootUser
from disbursement.models import Agent


@app.task()
def set_pin_error_mail(root_user_id):
    """
    related to disbursement.
    Send mail with set pin error to SuperAdmin.
    """
    root = RootUser.objects.filter(id=root_user_id).first()
    if not root:
        return
    super_admin = root.client.creator    
    agents_msisdns = Agent.objects.filter(
        wallet_provider=root).values_list('msisdn', flat=True)
    agents_msisdns = '-'.join(agents_msisdns)    
    message = _("""Dear {} 
        Please ask your wallet provider to reset pin for these mobile numbers
        {}
        Thanks, BR""")
    
    subject = f'[{root.brand.mail_subject}]'

    send_mail(
        from_email=settings.SERVER_EMAIL,
        recipient_list=[super_admin.email],
        subject=subject + ' Set Pin Notification',
        message=message.format(super_admin.username, agents_msisdns)
    )
