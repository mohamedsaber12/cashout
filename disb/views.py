# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import json
import logging
from datetime import datetime

import requests
from django.utils.translation import gettext as _
from django.utils import translation
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import redirect, render, render_to_response,get_object_or_404
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView,View
from rest_framework_expiring_authtoken.models import ExpiringToken

from data.decorators import otp_required
from data.models import Doc
from data.tasks import (generate_failed_disbursed_data, generate_success_disbursed_data, 
generate_all_disbursed_data)
from data.utils import redirect_params,get_client_ip
from disb.forms import VMTDataForm, AgentFormSet, AgentForm,BalanceInquiryPinForm
from disb.models import Agent, VMTData
from users.decorators import setup_required
from users.mixins import SuperRequiredMixin, SuperFinishedSetupMixin,RootRequiredMixin
from users.models import EntitySetup
from disbursement.utils import get_dot_env

DATA_LOGGER = logging.getLogger("disburse")
AGENT_CREATE_LOGGER = logging.getLogger("agent_create")
FAILED_DISBURSEMENT_DOWNLOAD = logging.getLogger(
    "failed_disbursement_download")
FAILED_VALIDATION_DOWNLOAD = logging.getLogger(
    "failed_validation_download")
WALLET_API_LOGGER = logging.getLogger("wallet_api")

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
        doc_obj = get_object_or_404(Doc, id=doc_id)
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
    doc_obj = get_object_or_404(Doc, id=doc_id)
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
        if request.is_ajax(): 
            if request.GET.get('export_failed') == 'true':
                generate_failed_disbursed_data.delay(doc_id, request.user.id,
                                    language=translation.get_language())
                return HttpResponse(status=200)
            elif request.GET.get('export_success') == 'true':
                generate_success_disbursed_data.delay(doc_id, request.user.id,
                                    language=translation.get_language())
                return HttpResponse(status=200)
            elif request.GET.get('export_all') == 'true':
                generate_all_disbursed_data.delay(doc_id, request.user.id,
                                                      language=translation.get_language())
                return HttpResponse(status=200)
        context = {
            'Ddata': doc_obj.disbursement_data.all(),
            'has_failed': doc_obj.disbursement_data.filter(is_disbursed=False).count() != 0,
            'has_success': doc_obj.disbursement_data.filter(is_disbursed=True).count() != 0,
            'doc_id': doc_id
        }
        return render(request, template_name='disbursement/list.html', context=context)

    return HttpResponse(status=401)


@setup_required
@login_required
def failed_disbursed_for_download(request, doc_id):
    doc_obj = get_object_or_404(Doc, id=doc_id)

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


@setup_required
@login_required
def download_failed_validation_file(request, doc_id):
    doc_obj = get_object_or_404(Doc, id=doc_id)
    can_view = (
        doc_obj.owner == request.user and request.user.is_maker
    )
    if not can_view:
        return HttpResponse(status=401)

    filename = request.GET.get('filename', None)
    if not filename:
        raise Http404

    file_path = "%s%s%s" % (settings.MEDIA_ROOT,
                            "/documents/disbursement/", filename)
    if not os.path.exists(file_path):
        raise Http404

    with open(file_path, 'rb') as fh:
        response = HttpResponse(
            fh.read(), content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
        FAILED_VALIDATION_DOWNLOAD.debug(
            f"user: {request.user.username} downloaded filename: {filename} at {datetime.now().strftime(' % d/%m/%Y % H: % M')}")
        return response

class SuperAdminAgentsSetup(SuperRequiredMixin, SuperFinishedSetupMixin, View):
    """
    View for super user to create Agents for the entity. 
    """
    template_name = 'entity/add_agent.html'

    def __init__(self,*args,**kwargs):
        super().__init__(*args, **kwargs)
        self.env = get_dot_env()

    def get_success_url(self,root):
        token, created = ExpiringToken.objects.get_or_create(user=root)
        if created:
            return reverse('users:add_fees', kwargs={'token': token.key})
        if token.expired():
            token.delete()
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
            
            agents_msisdn = [super_agent.msisdn]
            objs = agentform.save(commit=False)
            try:
                for obj in agentform.deleted_objects:
                    obj.delete()
            except AttributeError:
                pass
            for obj in objs:
                obj.wallet_provider = root
                agents_msisdn.append(obj.msisdn)

            if self.env.str('CALL_WALLETS', 'TRUE') == 'TRUE':
                transactions, error = self.validate_agent_wallet(
                    request, agents_msisdn)
                if not transactions:
                        # handle non form errors
                        context = {
                            "non_form_error":error,
                            "agentform": agentform,
                            "super_agent_form": super_agent_form,
                        }
                        return render(request, template_name=self.template_name, context=context)

                # transactions exist # check if have error or not #
                if self.error_exist(transactions):
                    return self.handle_form_errors(agentform, super_agent_form, transactions)

            super_agent.save()
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

    def validate_agent_wallet(self, request, msisdns):
        import requests
        vmt = VMTData.objects.get(vmt=request.user)
        data = vmt.return_vmt_data(VMTData.USER_INQUIRY)
        data["USERS"] = msisdns
        try:
            response = requests.post(
                self.env.str(vmt.vmt_environment), json=data, verify=False)
        except Exception as e:
            WALLET_API_LOGGER.debug(f"""
                {datetime.now().strftime('%d/%m/%Y %H:%M')}----> USER INQUIRY ERROR<--
                Users-> vmt(superadmin): {request.user.username}
                Error-> {e}""")
            return None, _("Agents creation process stopped during an internal error,\
                can you try again or contact you support team")

        WALLET_API_LOGGER.debug(f"""
            {datetime.now().strftime('%d/%m/%Y %H:%M')}----> USER INQUIRY <--
            Users-> vmt(superadmin): {request.user.username}
            Response-> {str(response.status_code)} -- {str(response.text)}""")
        if response.ok:
            response_dict = response.json()
            transactions = response_dict.get('TRANSACTIONS',None)
            if not transactions:
                error_message = response_dict.get(
                    'MESSAGE', None) or _("Agents creation failed")
                return None, error_message
            else:
                for agent in transactions:
                    if agent.get('HAS_PIN', None) == "TRUE":
                        error_message = "Agents already have registered and have a pin, For assistance call 7001"
                        return None, error_message
                    if agent.get("USER_TYPE") != "Super-Agent" and agent.get("USER_TYPE") != "Agent":
                        error_message = "Agents you have entered are not registered, For assistance call 7001"
                        return None, error_message
            return transactions, None
        return None, _("Agents creation process stopped during an internal error,\
                can you try again or contact you support team")

    def handle_form_errors(self,agentform, super_agent_form, transactions):
        # add errros from data to forms
        super_msisdn = super_agent_form.data.get('msisdn')
        super_msg = self.get_msg(super_msisdn,transactions)
        if super_msg:
            super_agent_form.add_error('msisdn', super_msg)
        for form in agentform.forms:
            msisdn = form.cleaned_data.get('msisdn')
            msg = self.get_msg(msisdn, transactions)
            if msg:
                form.add_error('msisdn', msg)

        context = {
            "agentform": agentform,
            "super_agent_form": super_agent_form,
        }
        return render(self.request, template_name=self.template_name, context=context)

    def error_exist(self,transactions):
        for trx in  transactions:
            valid = trx.get('USER_TYPE',None)
            if not valid:
                return True
        return False           

    def get_msg(self,msisdn,transactions):
        obj = list(filter(
            lambda trx: self.msisdn_slice(trx['MSISDN']) == msisdn, transactions))
        if not obj:
            return None
        obj = obj[0]
        valid = obj.get('USER_TYPE', None)
        if valid:
            return None
        return obj.get('MESSAGE', "Unknown error")

    def msisdn_slice(self,msisdn):
        return msisdn[-11:]

@method_decorator([setup_required], name='dispatch')
class BalanceInquiry(RootRequiredMixin, View):
    """
    View for super user to create Agents for the entity. 
    """
    template_name = 'disbursement/balance_inquiry.html'


    def get(self, request, *args, **kwargs):

        context = {
            "form" : BalanceInquiryPinForm()
        }
        return render(request, template_name=self.template_name, context=context)

    def post(self, request, *args, **kwargs):

        form = BalanceInquiryPinForm(request.POST)
        if not form.is_valid():
            context = {    
                "form":form
            }
            return render(request, template_name=self.template_name, context=context)
        
        ok, error_or_balance = self.get_wallet_balance(
            request, form.data.get('pin'))
        if ok:
            context = {
                "balance": error_or_balance,         
            }
        else:
            context = {
                "error_message": error_or_balance,
            }
        form = BalanceInquiryPinForm()
        context['form'] = form    
        return render(request, template_name=self.template_name, context=context)
   
    def get_wallet_balance(self, request,pin):
        import requests
        from disbursement.utils import get_dot_env
        env = get_dot_env()
        superadmin = request.user.root.client.creator
        vmt = VMTData.objects.get(vmt=superadmin)
        data = vmt.return_vmt_data(VMTData.BALANCE_INQUIRY)
        super_agent = Agent.objects.get(wallet_provider=request.user,super=True)
        data["MSISDN"]=  super_agent.msisdn
        data["PIN"]= pin
        try:
            response = requests.post(
                env.str(vmt.vmt_environment), json=data, verify=False)
        except Exception as e:
            WALLET_API_LOGGER.debug(f"""
                {datetime.now().strftime('%d/%m/%Y %H:%M')}----> BALANCE INQUIRY ERROR<--
                Users-> vmt(superadmin):{superadmin.username}
                Error-> {e}""")
            return False, _("Balance inquiry process stopped during an internal error,\
                can you try again or contact you support team")

        WALLET_API_LOGGER.debug(f"""
            {datetime.now().strftime('%d/%m/%Y %H:%M')}----> BALANCE INQUIRY <--
            Users-> vmt(superadmin):{superadmin.username}
            Response-> {str(response.status_code)} -- {str(response.text)}""")
        if response.ok:
            resp_json = response.json()
            if resp_json["TXNSTATUS"] == '200':
                return True, resp_json['BALANCE']
            error_message = resp_json.get(
                'MESSAGE', None) or _("Balance inquiry failed")
            return False, error_message
        return False, _("Balance inquiry process stopped during an internal error,\
                can you try again or contact you support team")

