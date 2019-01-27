# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging
from datetime import datetime

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render, render_to_response
from django.urls import reverse
from django.urls import reverse_lazy
from django.views.generic import CreateView
from rest_framework_expiring_authtoken.models import ExpiringToken

from data.decorators import otp_required
from data.models import Doc
from data.tasks import generate_file
from data.utils import redirect_params,get_client_ip
from disb.forms import VMTDataForm, AgentFormSet, AgentForm, PinForm
from disb.models import Agent, VMTData
from disb.resources import DisbursementDataResource
from users.decorators import setup_required
from users.mixins import SuperRequiredMixin
from users.models import EntitySetup
from users.tasks import send_agent_pin_to_client

DATA_LOGGER = logging.getLogger("disburse")
AGENT_CREATE_LOGGER = logging.getLogger("agent_create")
FAILED_DISBURSEMENT_DOWNLOAD = logging.getLogger(
    "failed_disbursement_download")

@setup_required
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
        can_disburse = doc_obj.can_user_disburse(request.user)[0]
        # request.user.is_verified = False  #TODO
        if doc_obj.owner.hierarchy == request.user.hierarchy and can_disburse and not doc_obj.is_disbursed:
            response = requests.post(
                request.scheme + "://" + request.get_host() +
                str(reverse_lazy("disbursement_api:disburse")),
                json={'doc_id': doc_id, 'pin': request.POST.get('pin'), 'user': request.user.username})
            DATA_LOGGER.debug(
                datetime.now().strftime('%d/%m/%Y %H:%M') + '----> DISBURSE VIEW RESPONSE <-- \n' + str(response.text))
            if response.ok:
                return redirect_params('data:doc_viewer', kw={'doc_id': doc_id},
                                       params={'disburse': 1, 'utm_redirect': 'success'})
            else:
                return redirect_params('data:doc_viewer', kw={'doc_id': doc_id}, params={'disburse': 0,
                                                                                         'utm_redirect': 'success'})

        owner = 'true' if doc_obj.owner.hierarchy == request.user.hierarchy else 'false'
        perm = 'true' if request.user.has_perm(
            'data.can_disburse') else 'false'
        doc_validated = 'false' if doc_obj.is_disbursed else 'true'
        return redirect_params('data:doc_viewer', kw={'doc_id': doc_id}, params={'disburse': -1,
                                                                                 'utm_redirect': 'success',
                                                                                 'utm_owner': owner,
                                                                                 'utm_perm': perm,
                                                                                 'utm_validate': doc_validated})

    else:
        response = reverse_lazy('data:doc_viewer', kwargs={'doc_id': doc_id})
        return redirect(response)

@setup_required
@login_required
def disbursement_list(request, doc_id):
    doc_obj = Doc.objects.get(id=doc_id)
    can_disburse = doc_obj.can_user_disburse(request.user)[0]
    if doc_obj.owner.hierarchy == request.user.hierarchy and can_disburse and doc_obj.is_disbursed:
        context = {
            'Ddata': doc_obj.disbursement_data.all(),
            'has_failed': doc_obj.disbursement_data.filter(is_disbursed=False).count() != 0
        }
    else:
        context = {'Ddata': None}
    context.update({'doc_id': doc_id})
    return render(request, template_name='disbursement/list.html', context=context)


@setup_required
@login_required
def generate_failed_disbursement_data(request, doc_id):
    doc_obj = Doc.objects.get(id=doc_id)
    can_disburse = doc_obj.can_user_disburse(request.user)[0]
    if doc_obj.owner.hierarchy == request.user.hierarchy and can_disburse and doc_obj.is_disbursed:
        generate_file_task = generate_file.delay(doc_id)
        return render(request,
                      template_name="disbursement/disbursement_file_download.html",
                      context={"task_id": str(generate_file_task.task_id), "media_url": settings.MEDIA_URL}
        )
    return HttpResponse(status=403)

@setup_required
@login_required
def failed_disbursed_for_download(request):
    task_id = request.GET.get("task_id")
    filename = request.GET.get("filename")

    if request.is_ajax():
        result = generate_file.AsyncResult(task_id)
        if result.ready():
            FAILED_DISBURSEMENT_DOWNLOAD.debug(f"user: {request.user.username} downloaded filename: {filename} at {datetime.now().strftime(' % d/%m/%Y % H: % M')}")
            return HttpResponse(json.dumps({"filename": result.get()}))
        FAILED_DISBURSEMENT_DOWNLOAD.debug(
            f'file not ready yet to be downloaded user: {request.user.username}')
        return HttpResponse(json.dumps({"filename": None}))

    else:
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=%s' % str(
            filename)
    return response


class SuperAdminAgentsSetup(SuperRequiredMixin, CreateView):
    """
    View for super user to create Agents for the entity. 
    """
    model = Agent
    form_class = AgentFormSet
    template_name = 'entity/add_agent.html'

    def get_success_url(self):
        return reverse('users:clients')

    def get_context_data(self, **kwargs):
        root = ExpiringToken.objects.get(key=self.kwargs['token']).user
        data = super().get_context_data(**kwargs)
        if not 'agentform' in data:
            data['agentform'] = self.form_class(
                queryset=Agent.objects.filter(
                    wallet_provider=root
                ),
                prefix='agents',
                form_kwargs={'root': root}
            )
        if not 'pinform' in data:
            data['pinform'] = PinForm()
        return data

    def post(self, request, *args, **kwargs):
        root = ExpiringToken.objects.get(key=self.kwargs['token']).user
        agentform = self.form_class(
            request.POST,
            queryset=Agent.objects.filter(
                wallet_provider=root
            ),
            prefix='agents',
            form_kwargs={'root': root}
        )
        pinform = PinForm(request.POST)
        if pinform.is_valid() and agentform.is_valid():
            agents_msisdn = []
            objs = agentform.save(commit=False)
            try:
                for obj in agentform.deleted_objects:
                    obj.delete()
            except AttributeError:
                pass
            for obj in objs:
                obj.set_pin(pinform.cleaned_data['pin'], False)
                obj.wallet_provider = root
                agents_msisdn.append(obj.msisdn)

            agentform.save()
            send_agent_pin_to_client.delay(pinform.cleaned_data['pin'], root.id)
            
            entity_setup = EntitySetup.objects.get(user=self.request.user,
                                                   entity=root)
            entity_setup.agents_setup = True
            entity_setup.save()
            AGENT_CREATE_LOGGER.debug( f'Agents created from IP Address {get_client_ip(self.request)} with msisdns {" - ".join(agents_msisdn)}')
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(agentform=agentform, pinform=pinform))

    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        kwargs = self.get_form_kwargs()
        kwargs.pop('instance')
        return form_class(**kwargs)
