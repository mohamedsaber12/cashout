# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

import logging
import requests
from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, render_to_response
from django.urls import reverse_lazy

from data.decorators import otp_required
from data.models import Doc
from data.tasks import generate_file
from data.utils import redirect_params
from disb.resources import DisbursementDataResource

DATA_LOGGER = logging.getLogger("disburse")


@otp_required
def disburse(request, doc_id):
    """
    Just to call the TOTP
    :param request:
    :param doc_id:
    :return:
    """
    if request.method == 'POST':
        doc_obj = Doc.objects.get(id=doc_id)
        # request.user.is_verified = False  #TODO
        if doc_obj.owner.hierarchy_id == request.user.hierarchy and request.user.has_perm(
                'data.can_disburse') and not doc_obj.is_disbursed:
            response = requests.post(
                request.scheme + "://" + request.get_host() + str(reverse_lazy("disbursement_api:disburse")),
                json={'doc_id': doc_id, 'pin': request.POST.get('pin'), 'user': request.user.username})
            DATA_LOGGER.debug(
                datetime.now().strftime('%d/%m/%Y %H:%M') + '----> DISBURSE VIEW RESPONSE <-- \n' + str(response.text))
            if response.ok:
                return redirect_params('data:doc_viewer', kw={'doc_id': doc_id},
                                       params={'disburse': 1, 'utm_redirect': 'success'})
            else:
                return redirect_params('data:doc_viewer', kw={'doc_id': doc_id}, params={'disburse': 0,
                                                                                         'utm_redirect': 'success'})

        owner = 'true' if doc_obj.owner.hierarchy_id == request.user.hierarchy else 'false'
        perm = 'true' if request.user.has_perm('data.can_disburse') else 'false'
        doc_validated = 'false' if doc_obj.is_disbursed else 'true'
        return redirect_params('data:doc_viewer', kw={'doc_id': doc_id}, params={'disburse': -1,
                                                                            'utm_redirect': 'success',
                                                                            'utm_owner': owner,
                                                                            'utm_perm': perm,
                                                                            'utm_validate': doc_validated})

    else:
        response = reverse_lazy('data:doc_viewer', kwargs={'doc_id': doc_id})
        return redirect(response)


@login_required
def disbursement_list(request, doc_id):
    doc_obj = Doc.objects.get(id=doc_id)
    if doc_obj.owner.hierarchy_id == request.user.hierarchy and request.user.has_perm(
            'data.can_disburse') and doc_obj.is_disbursed:
        context = {'Ddata': doc_obj.disbursement_data.all()}
    else:
        context = {'Ddata': None}
    context.update({'doc_id': doc_id})
    return render(request, template_name='disbursement/list.html', context=context)


@login_required
def generate_failed_disbursement_data(request, doc_id):
    doc_obj = Doc.objects.get(id=doc_id)
    if doc_obj.owner.hierarchy_id == request.user.hierarchy and request.user.has_perm(
            'data.can_disburse') and doc_obj.is_disbursed:
        generate_file_task = generate_file.delay(doc_id)
        return render_to_response("disbursement/disbursement_file_download.html", {"task_id": str(generate_file_task.task_id),
                                                                                   "media_url": settings.MEDIA_URL})


@login_required
def failed_disbursed_for_download(request):
    task_id = request.GET.get("task_id")
    filename = request.GET.get("filename")

    if request.is_ajax():
        result = generate_file.AsyncResult(task_id)
        if result.ready():
            return HttpResponse(json.dumps({"filename": result.get()}))
        return HttpResponse(json.dumps({"filename": None}))

    else:
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=%s' % str(filename)
    return response