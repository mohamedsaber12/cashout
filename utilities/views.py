# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import timedelta

from django.http import HttpResponse
from django.utils import timezone
from django.views import View

from users.models import RootUser

from .functions import render_to_pdf


class GeneratePDFView(View):
    """

    """

    def fetch_onboarded_entities_over_last_week(self, superadmin_username):
        one_week_ago = timezone.now() - timedelta(days=7)
        # ToDo: Select only new root created by certain super admin
        last_week_users = RootUser.objects.filter(date_joined__gte=one_week_ago).values('username', 'email', 'mobile_no')
        last_week_users_count = last_week_users.count()
        return {
            'entities': last_week_users,
            'entities_count': last_week_users_count
        }

    def get(self, request, *args, **kwargs):

        context = self.fetch_onboarded_entities_over_last_week('')
        pdf = render_to_pdf('utilities/new_entities_report.html', context_dict=context)
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            filename = f'weekly_report_{timezone.now().strftime("%Y_%m_%d_%H:%M:%S")}.pdf'
            content = f"attachment; filename={filename}"

            response['Content-Disposition'] = content
            return response

        return HttpResponse('Not Found')
