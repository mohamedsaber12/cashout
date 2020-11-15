# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os

import requests

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import translation
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import View, ListView

from rest_framework_expiring_authtoken.models import ExpiringToken

from core.models import AbstractBaseStatus
from data.decorators import otp_required
from data.models import Doc
from data.tasks import (generate_all_disbursed_data, generate_failed_disbursed_data, generate_success_disbursed_data)
from data.utils import redirect_params
from payouts.utils import get_dot_env
from users.decorators import setup_required
from users.mixins import (
    SuperFinishedSetupMixin, SuperRequiredMixin,
    SuperOrRootOwnsCustomizedBudgetClientRequiredMixin,
    SuperWithoutDefaultOnboardingPermissionRequired, UserWithDisbursementPermissionRequired,
)
from users.models import EntitySetup
from utilities import messages

from .forms import AgentForm, AgentFormSet, BalanceInquiryPinForm
from .models import Agent

DATA_LOGGER = logging.getLogger("disburse")
AGENT_CREATE_LOGGER = logging.getLogger("agent_create")
FAILED_DISBURSEMENT_DOWNLOAD = logging.getLogger("failed_disbursement_download")
FAILED_VALIDATION_DOWNLOAD = logging.getLogger("failed_validation_download")
WALLET_API_LOGGER = logging.getLogger("wallet_api")

MSG_TRY_OR_CONTACT = "can you try again or contact you support team"
MSG_AGENT_CREATION_ERROR = _(f"Agents creation process stopped during an internal error, {MSG_TRY_OR_CONTACT}")
MSG_BALANCE_INQUIRY_ERROR = _(f"Balance inquiry process stopped during an internal error, {MSG_TRY_OR_CONTACT}")

env = get_dot_env()


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
            DATA_LOGGER.debug(f"[message] [BULK DISBURSEMENT TO INTERNAL API] [{request.user}] -- doc_id: {doc_id}")
            response = requests.post(
                "https://" + request.get_host() + str(reverse_lazy("disbursement_api:disburse")),
                json={'doc_id': doc_id, 'pin': request.POST.get('pin'), 'user': request.user.username}
            )
            DATA_LOGGER.debug(f"[response] [BULK DISBURSEMENT VIEW RESPONSE] [{request.user}] -- {response.text}")
            if response.ok:
                return redirect_params('data:doc_viewer', kw={'doc_id': doc_id}, params={'disburse': 1,
                                                                                         'utm_redirect': 'success'})
            else:
                if response.status_code == 400:
                    return redirect_params('data:doc_viewer', kw={'doc_id': doc_id}, params={'disburse': 400,
                                                                                             'utm_redirect': 'success'})

                return redirect_params('data:doc_viewer', kw={'doc_id': doc_id}, params={'disburse': 0,
                                                                                         'utm_redirect': 'success'})

        owner = 'true' if doc_obj.owner.hierarchy == request.user.hierarchy else 'false'
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


@method_decorator([setup_required], name='dispatch')
class DisbursementDocTransactionsView(UserWithDisbursementPermissionRequired, View):
    """
    View for handling disbursed doc transactions list
    """

    def get(self, request, *args, **kwargs):
        """"""
        doc_id = self.kwargs.get("doc_id")
        doc_obj = get_object_or_404(Doc, id=doc_id)

        # 1. Is the user have the right to view this doc and the doc is disbursed
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
            # 2.1 If the request is ajax then prepare the disbursement report
            if request.is_ajax():
                # ToDo: Change this to handle bank sheets
                if request.GET.get('export_failed') == 'true':
                    generate_failed_disbursed_data.delay(doc_id, request.user.id, language=translation.get_language())
                    return HttpResponse(status=200)
                elif request.GET.get('export_success') == 'true':
                    generate_success_disbursed_data.delay(doc_id, request.user.id, language=translation.get_language())
                    return HttpResponse(status=200)
                elif request.GET.get('export_all') == 'true':
                    generate_all_disbursed_data.delay(doc_id, request.user.id, language=translation.get_language())
                    return HttpResponse(status=200)

            # 2.2 Prepare the context dict regarding the type of the doc
            if doc_obj.is_e_wallet:
                template_name = "disbursement/e_wallets_transactions_list.html"
                context = {
                    'doc_transactions': doc_obj.disbursement_data.all(),
                    'has_failed': doc_obj.disbursement_data.filter(is_disbursed=False).count() != 0,
                    'has_success': doc_obj.disbursement_data.filter(is_disbursed=True).count() != 0,
                    'is_normal_flow': request.user.root.root_entity_setups.is_normal_flow,
                }
            elif doc_obj.is_bank_wallet:
                template_name = "disbursement/bank_transactions_list.html"
                context = {
                    'doc_transactions': doc_obj.bank_wallets_transactions.all(),
                    'has_failed': doc_obj.bank_wallets_transactions.filter(
                            status=AbstractBaseStatus.FAILED
                    ).count() != 0,
                    'has_success': doc_obj.bank_wallets_transactions.filter(
                            status=AbstractBaseStatus.SUCCESSFUL
                    ).count() != 0,
                }
            elif doc_obj.is_bank_card:
                template_name = "disbursement/bank_transactions_list.html"
                context = {
                    'doc_transactions': doc_obj.bank_cards_transactions.all(),
                    'has_failed': doc_obj.bank_cards_transactions.filter(
                            status=AbstractBaseStatus.FAILED
                    ).count() != 0,
                    'has_success': doc_obj.bank_cards_transactions.filter(
                            status=AbstractBaseStatus.SUCCESSFUL
                    ).count() != 0,
                }

            context.update({'doc_obj': doc_obj})
            return render(request, template_name=template_name, context=context)

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

    filename = request.GET.get('filename', None)
    if not filename:
        raise Http404

    file_path = "%s%s%s" % (settings.MEDIA_ROOT, "/documents/disbursement/", filename)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(
                fh.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response['Content-Disposition'] = 'attachment; filename=%s' % filename
            FAILED_DISBURSEMENT_DOWNLOAD.debug(
                    f"[message] [DOWNLOAD FAILED DISBURSEMENT DOC] [{request.user}] -- doc_id: {doc_obj.id}"
            )
            return response
    else:
        raise Http404


@setup_required
@login_required
def download_failed_validation_file(request, doc_id):
    doc_obj = get_object_or_404(Doc, id=doc_id)
    can_view = (doc_obj.owner == request.user and request.user.is_maker)
    if not can_view:
        return HttpResponse(status=401)

    filename = request.GET.get('filename', None)
    if not filename:
        raise Http404

    file_path = "%s%s%s" % (settings.MEDIA_ROOT, "/documents/disbursement/", filename)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(
                fh.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response['Content-Disposition'] = 'attachment; filename=%s' % filename
            FAILED_VALIDATION_DOWNLOAD.debug(
                    f"[message] [DOWNLOAD FAILED VALIDATIONS DOC] [{request.user}] -- doc_id: {doc_obj.id}"
            )
            return response
    else:
        raise Http404


class SuperAdminAgentsSetup(SuperRequiredMixin, SuperFinishedSetupMixin, View):
    """
    View for super user to create Agents for the entity.
    """
    template_name = 'entity/add_agent.html'

    def get_success_url(self, root):
        token, created = ExpiringToken.objects.get_or_create(user=root)
        if created:
            return reverse('users:add_fees', kwargs={'token': token.key})
        if token.expired():
            token.delete()
            token = ExpiringToken.objects.create(user=root)
        return reverse('users:add_fees', kwargs={'token': token.key})

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests to the SuperAdminAgentsSetup view
        """
        root = ExpiringToken.objects.get(key=self.kwargs['token']).user
        context = {
            'agentform': AgentFormSet(
                queryset=Agent.objects.filter(wallet_provider=root, super=False),
                prefix='agents',
                form_kwargs={'root': root}
            ),

            'super_agent_form':  AgentForm(
                initial=Agent.objects.filter(wallet_provider=root, super=False),
                root=root
            )
        }
        return render(request, template_name=self.template_name, context=context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests to the SuperAdminAgentsSetup view
        """
        root = ExpiringToken.objects.get(key=self.kwargs['token']).user
        data = request.POST.copy()          # pop superagent data
        data.pop('msisdn', None)
        agentform = AgentFormSet(
            data,
            queryset=Agent.objects.filter(wallet_provider=root),
            prefix='agents',
            form_kwargs={'root': root}
        )
        super_agent_form = AgentForm({'msisdn': request.POST.get('msisdn')}, root=root)

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

            if root.callwallets_moderator.first().user_inquiry:
                transactions, error = self.validate_agent_wallet(request, agents_msisdn)
                if not transactions:                        # handle non form errors
                    context = {
                        "non_form_error": error,
                        "agentform": agentform,
                        "super_agent_form": super_agent_form,
                    }
                    return render(request, template_name=self.template_name, context=context)

                if self.error_exist(transactions):          # transactions exist # check if have error or not #
                    return self.handle_form_errors(agentform, super_agent_form, transactions)

            super_agent.save()
            agentform.save()
            entity_setup = EntitySetup.objects.get(user=self.request.user, entity=root)
            entity_setup.agents_setup = True
            entity_setup.save()
            AGENT_CREATE_LOGGER.debug(
                    f"[message] [AGENTS CREATED] [{self.request.user}] -- agents: {' , '.join(agents_msisdn)}"
            )
            return HttpResponseRedirect(self.get_success_url(root))
        else:
            context = {
                "agentform": agentform,
                "super_agent_form": super_agent_form
            }
            return render(request, template_name=self.template_name, context=context)

    def validate_agent_wallet(self, request, msisdns):
        superadmin = request.user
        payload = superadmin.vmt.accumulate_user_inquiry_payload(msisdns)
        try:
            WALLET_API_LOGGER.debug(f"[request] [USER INQUIRY] [{request.user}] -- {payload}")
            response = requests.post(env.str(superadmin.vmt.vmt_environment), json=payload, verify=False)
        except Exception as e:
            WALLET_API_LOGGER.debug(f"[message] [USER INQUIRY ERROR] [{request.user}] -- Error: {e.args}")
            return None, MSG_AGENT_CREATION_ERROR
        else:
            WALLET_API_LOGGER.debug(f"[response] [USER INQUIRY] [{request.user}] -- {str(response.text)}")

        if response.ok:
            response_dict = response.json()
            transactions = response_dict.get('TRANSACTIONS', None)
            if not transactions:
                error_message = response_dict.get('MESSAGE', None) or _("Agents creation failed")
                return None, error_message
            else:
                for agent in transactions:
                    if agent.get('HAS_PIN', None):
                        error_message = f"Agents already have registered and have a pin, {messages.MSG_TRY_OR_CONTACT}"
                        return None, error_message
                    if agent.get("USER_TYPE") != "Super-Agent" and agent.get("USER_TYPE") != "Agent":
                        error_message = f"Agents you have entered are not registered, {messages.MSG_TRY_OR_CONTACT}"
                        return None, error_message
            return transactions, None
        return None, MSG_AGENT_CREATION_ERROR

    def handle_form_errors(self, agentform, super_agent_form, transactions):
        """
        :return: Add errors from data to forms
        """
        super_msisdn = super_agent_form.data.get('msisdn')
        super_msg = self.get_msg(super_msisdn, transactions)
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

    def error_exist(self, transactions):
        for trx in transactions:
            valid = trx.get('USER_TYPE', None)
            if not valid:
                return True
        return False

    def get_msg(self, msisdn, transactions):
        obj = list(filter(lambda trx: self.msisdn_slice(trx['MSISDN']) == msisdn, transactions))
        if not obj:
            return None
        obj = obj[0]
        valid = obj.get('USER_TYPE', None)
        if valid:
            return None
        return obj.get('MESSAGE', "Unknown error")

    def msisdn_slice(self, msisdn):
        return msisdn[-11:]


@method_decorator([setup_required], name='dispatch')
class BalanceInquiry(SuperOrRootOwnsCustomizedBudgetClientRequiredMixin, View):
    """
    ToDo: Remove the custom budget handling for manual patch and handle custom budget for instant admins
    View for SuperAdmin and Root user to inquire for the balance of a certain entity.
    Scenarios:
        1. The Regular Way:
            - Root has not custom budget, so:
                A) SuperAdmin user can't make balance inquiry at this Root user's balance.
                B) Root user's balance inquiry will be made at the whole super agent balance.
        2. The Customized Way:
            - Root has custom budget, so:
                A) Root user will have custom budget defined by the system administrator for the first time.
                B) SuperAdmin user can add new budget to his/her own Root users' with customized budgets, using
                    icons at the Root user's cards (Clients page).
                C) SuperAdmin user can make balance inquiry at this specific Root user with the custom budget.
                D) Root user's balance inquiry will be made at the customized budget only.
    """
    template_name = 'disbursement/balance_inquiry.html'

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests to the balance inquiry view
        """
        context = {
            "form": BalanceInquiryPinForm(),
            "username": self.kwargs.get("username")
        }
        return render(request, template_name=self.template_name, context=context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests to the balance inquiry view
        """
        context = {
            "form": BalanceInquiryPinForm(request.POST),
            "username": self.kwargs.get("username")
        }

        if not context["form"].is_valid():
            context = context
            return render(request, template_name=self.template_name, context=context)

        if request.user.is_root:
            ok, error_or_balance = self.get_wallet_balance(request, context["form"].data.get('pin'))
        else:
            ok, error_or_balance = self.get_wallet_balance(
                    request=request,
                    pin=context["form"].data.get('pin'),
                    entity_username=context["username"]
            )

        if ok:
            context.update({"balance": error_or_balance})
        else:
            context.update({"error_message": error_or_balance})
        context.update({"form": BalanceInquiryPinForm()})
        return render(request, template_name=self.template_name, context=context)

    def get_wallet_balance(self, request, pin, entity_username=None):
        if request.user.is_root:
            superadmin = request.user.root.client.creator
            super_agent = Agent.objects.get(wallet_provider=request.user, super=True)
        else:
            superadmin = request.user
            super_agent = Agent.objects.get(wallet_provider__username=entity_username, super=True)

        payload, refined_payload = superadmin.vmt.accumulate_balance_inquiry_payload(super_agent.msisdn, pin)

        try:
            WALLET_API_LOGGER.debug(f"[request] [BALANCE INQUIRY] [{request.user}] -- {refined_payload}")
            response = requests.post(env.str(superadmin.vmt.vmt_environment), json=payload, verify=False)
        except Exception as e:
            WALLET_API_LOGGER.debug(f"[message] [BALANCE INQUIRY ERROR] [{request.user}] -- Error: {e.args}")
            return False, MSG_BALANCE_INQUIRY_ERROR
        else:
            WALLET_API_LOGGER.debug(f"[response] [BALANCE INQUIRY] [{request.user}] -- {response.text}")

        if response.ok:
            resp_json = response.json()

            if resp_json["TXNSTATUS"] == '200':
                if request.user.is_superadmin or request.user.root:
                    return True, resp_json['BALANCE']

            error_message = resp_json.get('MESSAGE', None) or _("Balance inquiry failed")
            return False, error_message
        return False, MSG_BALANCE_INQUIRY_ERROR


class AgentsListView(SuperWithoutDefaultOnboardingPermissionRequired, ListView):
    """
    View for enabling superadmins to list their own agents
    """

    model = Agent
    context_object_name = "agents_list"
    template_name = "disbursement/agents.html"

    def get_queryset(self):
        return Agent.objects.filter(wallet_provider=self.request.user)
