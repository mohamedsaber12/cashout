# -*- coding: UTF-8 -*-
from __future__ import print_function

from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import gettext as _
from disbursement.settings.celery import app
from users.models import RootUser

@app.task()
def send_agent_pin_to_client(pin_raw,root_user_id):
    root = RootUser.objects.filter(id=root_user_id).first()
    if not root:
        return
    message = f"""Dear Client 
        The agent pin is: {pin_raw}
        Thanks, BR"""
    send_mail(
        from_email=settings.SERVER_EMAIL,
        recipient_list=[root.email],
        subject='[Payroll] Pin Notification',
        message=message
    )
