# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
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
from django.views.generic import CreateView,View
from rest_framework_expiring_authtoken.models import ExpiringToken

from data.decorators import otp_required
from data.models import Doc
from data.tasks import generate_file
from data.utils import redirect_params,get_client_ip
from disb.forms import VMTDataForm, AgentFormSet, AgentForm
from disb.models import Agent, VMTData
from disb.resources import DisbursementDataResource
from users.decorators import setup_required
from users.mixins import SuperRequiredMixin, SuperFinishedSetupMixin
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

    can_view = (
        doc_obj.owner.hierarchy == request.user.hierarchy and
        (
            doc_obj.owner == request.user or
            request.user.is_checker or
            request.user.is_root
        ) and
        doc_obj.is_disbursed
    )
    if can_view:
        if request.is_ajax() and request.GET.get('export_failed') == 'true':
            generate_file.delay(doc_id,request.user.id)
            return HttpResponse(status=200)
        context = {
            'Ddata': doc_obj.disbursement_data.all(),
            'has_failed': doc_obj.disbursement_data.filter(is_disbursed=False).count() != 0,
            'doc_id': doc_id
        }
        return render(request, template_name='disbursement/list.html', context=context)

    return HttpResponse(status=401)


@setup_required
@login_required
def failed_disbursed_for_download(request, doc_id):
    doc_obj = Doc.objects.get(id=doc_id)

    can_view = (
        doc_obj.owner.hierarchy == request.user.hierarchy and
        (
            doc_obj.owner == request.user or
            request.user.is_checker or
            request.user.is_root
        ) and
        doc_obj.is_disbursed
    )
    if not can_view:
        return HttpResponse(status=401)

    filename = request.GET.get('filename',None)
    if not filename:
        raise Http404
      
    file_path = "%s%s%s" % (settings.MEDIA_ROOT,
                        "/documents/disbursement/", filename)
    if not os.path.exists(file_path):
        raise Http404

    with open(file_path, 'rb') as fh:
        response = HttpResponse(fh.read(), content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
        response['X-Accel-Redirect'] = file_path
        FAILED_DISBURSEMENT_DOWNLOAD.debug(
            f"user: {request.user.username} downloaded filename: {filename} at {datetime.now().strftime(' % d/%m/%Y % H: % M')}")

        return response
    

class SuperAdminAgentsSetup(SuperRequiredMixin, SuperFinishedSetupMixin, View):
    """
    View for super user to create Agents for the entity. 
    """
    template_name = 'entity/add_agent.html'

    def get_success_url(self,root):
        token, created = ExpiringToken.objects.get_or_create(user=root)
        if created:
            return reverse('users:add_fees', kwargs={'token': token.key})
        if token.expired():
            token = ExpiringToken.objects.create(user=root)
        return reverse('users:add_fees', kwargs={'token': token.key})
        

    def get(self,request,*args, **kwargs):
        root = ExpiringToken.objects.get(key=self.kwargs['token']).user
        context = {
            'agentform' : AgentFormSet(
                queryset=Agent.objects.filter(wallet_provider=root,super = False),
                prefix='agents',
                form_kwargs={'root': root}
            ),

            'super_agent_form':  AgentForm(
                initial=Agent.objects.filter(wallet_provider=root,super=False),
                root = root
            )
        }
        return render(request, template_name=self.template_name, context=context)


    def post(self, request, *args, **kwargs):
        root = ExpiringToken.objects.get(key=self.kwargs['token']).user
        # pop superagent data
        data = request.POST.copy()
        data.pop('msisdn',None)
        agentform = AgentFormSet(
            data,
            queryset=Agent.objects.filter(
                wallet_provider=root
            ),
            prefix='agents',
            form_kwargs={'root': root}
        )
        super_agent_form = AgentForm(
            {'msisdn': request.POST.get('msisdn')}, root=root)
        if agentform.is_valid() and super_agent_form.is_valid():
            super_agent = super_agent_form.save(commit=False)
            super_agent.super = True
            super_agent.wallet_provider = root
            super_agent.save()

            agents_msisdn = []
            objs = agentform.save(commit=False)
            try:
                for obj in agentform.deleted_objects:
                    obj.delete()
            except AttributeError:
                pass
            for obj in objs:
                obj.wallet_provider = root
                agents_msisdn.append(obj.msisdn)

            agentform.save()
            
            entity_setup = EntitySetup.objects.get(user=self.request.user,
                                                   entity=root)
            entity_setup.agents_setup = True
            entity_setup.save()
            AGENT_CREATE_LOGGER.debug( f'Agents created from IP Address {get_client_ip(self.request)} with msisdns {" - ".join(agents_msisdn)}')
            return HttpResponseRedirect(self.get_success_url(root))
        else:
            context = {
                "agentform" : agentform,
                "super_agent_form" : super_agent_form,
            }
            return render(request, template_name=self.template_name, context=context)

    
