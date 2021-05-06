# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import io
import logging
import os
import random
import xlwt
from decimal import Decimal
from django.utils import timezone

from faker import Factory as fake_factory
import pandas as pd
import requests

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import translation
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import ListView, View
from django.utils.timezone import datetime, make_aware
from django.db.models import Case, Count, F, Q, Sum, When

import urllib


from rest_framework import status
from rest_framework_expiring_authtoken.models import ExpiringToken

from core.models import AbstractBaseStatus
from data.decorators import otp_required
from data.models import Doc
from data.tasks import (ExportClientsTransactionsMonthlyReportTask,
                        generate_all_disbursed_data,
                        generate_failed_disbursed_data,
                        generate_success_disbursed_data)
from data.utils import redirect_params
from instant_cashin.specific_issuers_integrations import BankTransactionsChannel
from payouts.utils import get_dot_env
from users.decorators import setup_required
from users.mixins import (SuperFinishedSetupMixin,
                          SuperOrRootOwnsCustomizedBudgetClientRequiredMixin,
                          SuperRequiredMixin,
                          AgentsListPermissionRequired,
                          UserWithAcceptVFOnboardingPermissionRequired,
                          UserWithDisbursementPermissionRequired)
from users.models import EntitySetup, Client, RootUser, User
from utilities import messages
from utilities.models import Budget

from .forms import (ExistingAgentForm, AgentForm, AgentFormSet, ExistingAgentFormSet,
                    BalanceInquiryPinForm, SingleStepTransactionForm)
from .mixins import AdminOrCheckerOrSupportRequiredMixin
from .models import Agent, BankTransaction, DisbursementData
from .utils import (VALID_BANK_CODES_LIST, VALID_BANK_TRANSACTION_TYPES_LIST,
                    DEFAULT_LIST_PER_ADMIN_FOR_TRANSACTIONS_REPORT_raseedy_vf,
                    add_fees_and_vat_to_qs,
                    DEFAULT_LIST_PER_ADMIN_FOR_TRANSACTIONS_REPORT,
                    DEFAULT_PER_ADMIN_FOR_VF_FACILITATOR_TRANSACTIONS_REPORT,
                    determine_trx_category_and_purpose)
from instant_cashin.models import AbstractBaseIssuer, InstantTransaction
from data.utils import deliver_mail, export_excel, randomword 
from instant_cashin.utils import get_from_env
from utilities.models.abstract_models import AbstractBaseACHTransactionStatus


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
            http_or_https = "http://" if get_from_env("ENVIRONMENT") == "local" else "https://"
            
            response = requests.post(
                http_or_https + request.get_host() + str(reverse_lazy("disbursement_api:disburse")),
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

    @staticmethod
    def get_document_transactions_totals(doc_obj, doc_transactions):
        """Returns aggregated totals for specific doc"""

        # Handle e-wallets docs -vodafone/etisalat/aman-
        if doc_obj.is_e_wallet:
            pending_transactions = doc_transactions.filter(reason='').\
                values('is_disbursed').annotate(total_amount=Sum('amount'), number=Count('id')).order_by()
            failed_transactions = doc_transactions.filter(~Q(reason=''), is_disbursed=False).\
                values('is_disbursed').annotate(total_amount=Sum('amount'), number=Count('id')).order_by()
            success_transactions = doc_transactions.filter(is_disbursed=True).\
                values('is_disbursed').annotate(total_amount=Sum('amount'), number=Count('id')).order_by()
            doc_transactions_totals = {
                'P': pending_transactions[0] if pending_transactions else None,
                'F': failed_transactions[0] if failed_transactions else None,
                'S': success_transactions[0] if success_transactions else None
            }

        # Handle bank cards/wallets/orange docs
        elif doc_obj.is_bank_wallet or doc_obj.is_bank_card:
            trx_id = 'uid' if doc_obj.is_bank_wallet else 'id'
            doc_transactions_totals = doc_transactions.values('status').\
                annotate(total_amount=Sum('amount'), number=Count(trx_id)).order_by()

            doc_transactions_totals = { agg_dict['status']: agg_dict for agg_dict in doc_transactions_totals }
            if doc_transactions_totals.get('d') and doc_transactions_totals.get('P'):
                doc_transactions_totals['P']['total_amount'] += doc_transactions_totals.get('d').get('total_amount')
                doc_transactions_totals['P']['number'] += doc_transactions_totals.get('d').get('number')
            elif doc_transactions_totals.get('d'):
                doc_transactions_totals['P'] = doc_transactions_totals.get('d')

        doc_transactions_totals['all'] = {
            'total_amount' : doc_obj.total_amount,
            'number' : doc_obj.total_count
        }
        return doc_transactions_totals

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
                doc_transactions = doc_obj.disbursement_data.all()

                context = {
                    'doc_transactions': doc_transactions,
                    'has_failed': doc_obj.disbursement_data.filter(is_disbursed=False).count() != 0,
                    'has_success': doc_obj.disbursement_data.filter(is_disbursed=True).count() != 0,
                    'is_normal_flow': request.user.root.root_entity_setups.is_normal_flow,
                }
            elif doc_obj.is_bank_wallet:
                template_name = "disbursement/bank_transactions_list.html"
                doc_transactions = doc_obj.bank_wallets_transactions.all()

                context = {
                    'doc_transactions': doc_transactions,
                    'has_failed': doc_obj.bank_wallets_transactions.filter(
                            status=AbstractBaseStatus.FAILED
                    ).count() != 0,
                    'has_success': doc_obj.bank_wallets_transactions.filter(
                            status=AbstractBaseStatus.SUCCESSFUL
                    ).count() != 0,
                }
            elif doc_obj.is_bank_card:
                template_name = "disbursement/bank_transactions_list.html"
                bank_trx_ids = BankTransaction.objects.filter(document=doc_obj).\
                    order_by("parent_transaction__transaction_id", "-id").\
                    distinct("parent_transaction__transaction_id").\
                    values_list("id", flat=True)
                doc_transactions = BankTransaction.objects.filter(id__in=bank_trx_ids).order_by("-created_at")

                context = {
                    'doc_transactions': doc_transactions,
                    'has_failed': doc_obj.bank_cards_transactions.filter(
                            status=AbstractBaseStatus.FAILED
                    ).count() != 0,
                    'has_success': doc_obj.bank_cards_transactions.filter(
                            status=AbstractBaseStatus.SUCCESSFUL
                    ).count() != 0,
                }
            # add fees and vat to query set in case of accept model
            context['doc_transactions'] = add_fees_and_vat_to_qs(
                context['doc_transactions'],
                request.user.root,
                doc_obj
            )
            context.update({
                'doc_obj': doc_obj,
                'doc_transactions_totals': self.__class__.get_document_transactions_totals(doc_obj, doc_transactions),
            })
            return render(request, template_name=template_name, context=context)

        return HttpResponse(status=401)


class ExportClientsTransactionsReportPerSuperAdmin(SuperRequiredMixin, View):
    """
    View for exporting clients aggregated transactions report per super admin
    """

    def get(self, request, *args, **kwargs):
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        status = request.GET.get('status', None)

        if request.is_ajax():
            # ExportClientsTransactionsMonthlyReportTask.delay(request.user.id, start_date, end_date, status)
            exportObject = ExportClientsTransactionsMonthlyReport()
            report_download_url = exportObject.run(request.user.id, start_date, end_date, status)
            return HttpResponse(report_download_url)

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

@login_required
def download_exported_transactions(request):
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
                    f"[message] [DOWNLOAD EXPORTED TRANSACTIONS] [{request.user}] -- file name: {filename}"
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

    def validate_agent_wallet(self, request, msisdns):
        superadmin = request.user
        payload = superadmin.vmt.accumulate_user_inquiry_payload(msisdns)
        try:
            WALLET_API_LOGGER.debug(f"[request] [user inquiry] [{request.user}] -- {payload}")
            response = requests.post(env.str(superadmin.vmt.vmt_environment), json=payload, verify=False)
        except Exception as e:
            WALLET_API_LOGGER.debug(f"[message] [user inquiry error] [{request.user}] -- Error: {e.args}")
            return None, MSG_AGENT_CREATION_ERROR
        else:
            WALLET_API_LOGGER.debug(f"[response] [user inquiry] [{request.user}] -- {str(response.text)}")

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
                    if agent.get("USER_TYPE") != "Super-Agent" and agent.get("USER_TYPE") != "Agent" \
                            and agent.get("USER_TYPE") != "P2M-Merchant":
                        error_message = f"Agents you have entered are not registered, {messages.MSG_TRY_OR_CONTACT}"
                        return None, error_message
            return transactions, None
        return None, MSG_AGENT_CREATION_ERROR

    def handle_form_errors(self, agents_formset, super_agent_form, transactions):
        """
        :return: Add errors from data to forms
        """
        super_msisdn = super_agent_form.data.get('msisdn')
        super_msg = self.get_msg(super_msisdn, transactions)

        if super_msg:
            super_agent_form.add_error('msisdn', super_msg)
        if agents_formset:
            for form in agents_formset.forms:
                msisdn = form.cleaned_data.get('msisdn')
                msg = self.get_msg(msisdn, transactions)
                if msg:
                    form.add_error('msisdn', msg)

            context = {
                "agents_formset": agents_formset,
                "super_agent_form": super_agent_form,
            }
        else:
            context = {"super_agent_form": super_agent_form}

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

    def dispatch(self, request, *args, **kwargs):
        """
        Common attributes between GET and POST methods
        """
        self.root = ExpiringToken.objects.get(key=self.kwargs['token']).user

        if self.root.client.agents_onboarding_choice in \
                [Client.EXISTING_SUPERAGENT_NEW_AGENTS, Client.EXISTING_SUPERAGENT_AGENTS]:
            superadmin_children = request.user.children()
            agents_of_all_types = Agent.objects.filter(wallet_provider__in=superadmin_children).distinct('msisdn')
            existing_super_agents = agents_of_all_types.filter(super=True).exclude(type__in=[Agent.P2M])
            existing_non_super_agents = agents_of_all_types.filter(super=False)
            self.super_agents_choices = [(agent.msisdn, agent.msisdn) for agent in existing_super_agents]
            self.non_super_agents_choices = [(agent.msisdn, agent.msisdn) for agent in existing_non_super_agents]

        return super().dispatch(request, *args, **kwargs)

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
        if self.root.client.agents_onboarding_choice in \
                [Client.NEW_SUPERAGENT_AGENTS, Client.EXISTING_SUPERAGENT_NEW_AGENTS]:
            context = {
                'agents_formset': AgentFormSet(
                        queryset=Agent.objects.filter(wallet_provider=self.root, super=False),
                        prefix='agents',
                        form_kwargs={'root': self.root}
                )
            }
            if self.root.client.agents_onboarding_choice == Client.NEW_SUPERAGENT_AGENTS:
                context['super_agent_form'] = AgentForm(
                        initial=Agent.objects.filter(wallet_provider=self.root, super=False),
                        root=self.root
                )

        elif self.root.client.agents_onboarding_choice == Client.EXISTING_SUPERAGENT_AGENTS:
            context = {
                'agents_formset': ExistingAgentFormSet(
                        queryset=Agent.objects.filter(wallet_provider=self.root, super=False),
                        prefix='agents',
                        form_kwargs={'root': self.root, 'agents_choices': self.non_super_agents_choices}
                )
            }

        # Handle P2M choice
        else:
            context = {
                'super_agent_form': AgentForm(
                        initial=Agent.objects.filter(wallet_provider=self.root, super=False),
                        root=self.root
                )
            }

        if self.root.client.agents_onboarding_choice in \
                [Client.EXISTING_SUPERAGENT_NEW_AGENTS, Client.EXISTING_SUPERAGENT_AGENTS]:
            context['super_agent_form'] = ExistingAgentForm(
                    initial=Agent.objects.filter(wallet_provider=self.root, super=False),
                    root=self.root,
                    agents_choices=self.super_agents_choices
            )
        return render(request, template_name=self.template_name, context=context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests to the SuperAdminAgentsSetup view
        """
        data = request.POST.copy()          # pop superagent data
        data.pop('msisdn', None)

        # 1. Handle POST form request of existing superagent and existing agents
        if self.root.client.agents_onboarding_choice == Client.EXISTING_SUPERAGENT_AGENTS:
            agents_formset = ExistingAgentFormSet(
                    data,
                    queryset=Agent.objects.filter(wallet_provider=self.root),
                    prefix='agents',
                    form_kwargs={'root': self.root, 'agents_choices': self.non_super_agents_choices}
            )
            super_agent_form = ExistingAgentForm(
                    {'msisdn': request.POST.get('msisdn')},
                    root=self.root,
                    agents_choices=self.super_agents_choices
            )

        # 2. Handle the other 3 types [(new superagent, new agents), (existing superagent, new agents), (p2m)]
        else:
            # 2.1 Handle POST form request of existing superagent
            if self.root.client.agents_onboarding_choice == Client.EXISTING_SUPERAGENT_NEW_AGENTS:
                super_agent_form = ExistingAgentForm(
                        {'msisdn': request.POST.get('msisdn')},
                        root=self.root,
                        agents_choices=self.super_agents_choices
                )

            # 2.2 Handle POST form request of new superagent type or p2m
            else:
                super_agent_form = AgentForm({'msisdn': request.POST.get('msisdn')}, root=self.root)

            agents_formset = AgentFormSet(
                    data,
                    queryset=Agent.objects.filter(wallet_provider=self.root),
                    prefix='agents',
                    form_kwargs={'root': self.root}
            )

        # 1. If agent type is P2M and the form is valid
        if self.root.client.agents_onboarding_choice == Client.P2M and super_agent_form.is_valid():
            super_agent = super_agent_form.save(commit=False)
            super_agent.super = True
            super_agent.type = Agent.P2M
            super_agent.wallet_provider = self.root
            agents_msisdn = [super_agent.msisdn]

            if self.root.callwallets_moderator.first().user_inquiry:
                transactions, error = self.validate_agent_wallet(request, agents_msisdn)
                if not transactions:                        # handle non form errors
                    context = {
                        "non_form_error": error,
                        "super_agent_form": super_agent_form,
                    }
                    return render(request, template_name=self.template_name, context=context)

                if self.error_exist(transactions):          # transactions exist # check if have error or not #
                    return self.handle_form_errors(None, super_agent_form, transactions)

        # 2. If agent type in
        #   [(new superagent, new agents), (existing superagent, new agents), (existing superagent, existing agents)]
        #   and the form is valid
        elif agents_formset.is_valid() and super_agent_form.is_valid():
            super_agent = super_agent_form.save(commit=False)
            objs = agents_formset.save(commit=False)
            super_agent.super = True
            super_agent.wallet_provider = self.root
            agents_msisdn = []

            if not self.root.client.agents_onboarding_choice == Client.EXISTING_SUPERAGENT_NEW_AGENTS:
                agents_msisdn.append(super_agent.msisdn)

            try:
                for obj in agents_formset.deleted_objects:
                    obj.delete()
            except AttributeError:
                pass
            for obj in objs:
                obj.wallet_provider = self.root
                agents_msisdn.append(obj.msisdn)

            if self.root.callwallets_moderator.first().user_inquiry and \
                    not self.root.client.agents_onboarding_choice == Client.EXISTING_SUPERAGENT_AGENTS:
                transactions, error = self.validate_agent_wallet(request, agents_msisdn)
                if not transactions:                        # handle non form errors
                    context = {
                        "non_form_error": error,
                        "agents_formset": agents_formset,
                        "super_agent_form": super_agent_form,
                    }
                    return render(request, template_name=self.template_name, context=context)

                if self.error_exist(transactions):          # transactions exist # check if have error or not #
                    return self.handle_form_errors(agents_formset, super_agent_form, transactions)

            agents_formset.save()

        # 3. The forms is not valid
        else:
            context = {
                "agents_formset": agents_formset,
                "super_agent_form": super_agent_form
            }
            return render(request, template_name=self.template_name, context=context)

        super_agent.save()
        entity_setup = EntitySetup.objects.get(user=self.request.user, entity=self.root)
        entity_setup.agents_setup = True
        entity_setup.save()
        AGENT_CREATE_LOGGER.debug(
                f"[message] [agents created] [{self.request.user}] -- agents: {' , '.join(agents_msisdn)}"
        )
        return HttpResponseRedirect(self.get_success_url(self.root))

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


class AgentsListView(AgentsListPermissionRequired, ListView):
    """
    View for enabling superadmins to list their own agents
    """

    model = Agent
    context_object_name = "agents_list"
    template_name = "disbursement/agents.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['admin'] = self.request.GET.get("admin")
        return context

    def get_queryset(self):
        if self.request.user.is_support and (self.request.user.is_vodafone_default_onboarding or self.request.user.is_banks_standard_model_onboaring):
            return Agent.objects.filter(wallet_provider__username=self.request.GET.get("admin"))
        return Agent.objects.filter(wallet_provider=self.request.user)


class SingleStepTransactionsView(AdminOrCheckerOrSupportRequiredMixin, View):
    """
    List/Create view for single step bank transactions over the manual patch
    """

    model = BankTransaction
    context_object_name = 'transactions_list'
    template_name = 'disbursement/single_step_trx_list.html'

    def get_queryset(self):
        user_hierarchy = self.request.user.hierarchy
        if self.request.user.is_support and self.request.GET.get("admin_hierarchy"):
            user_hierarchy = self.request.GET.get("admin_hierarchy")
            root_user = RootUser.objects.filter(hierarchy=user_hierarchy).first()
        else:
            root_user = self.request.user.root
        if self.request.GET.get('issuer', None) == 'wallets':
            trxs = InstantTransaction.objects.filter(
                from_user__hierarchy=user_hierarchy, is_single_step=True).order_by("-created_at")
        else:
            bank_trx_ids = BankTransaction.objects.\
                filter(user_created__hierarchy=user_hierarchy, is_single_step=True).\
                order_by("parent_transaction__transaction_id", "-id").\
                distinct("parent_transaction__transaction_id").\
                values_list("id", flat=True)

            trxs = BankTransaction.objects.filter(id__in=bank_trx_ids).order_by("-created_at")
        # add fees and vat to query set in case of accept model
        return add_fees_and_vat_to_qs(
            trxs,
            root_user,
            None
        )

    def get(self, request, *args, **kwargs):
        """Handles GET requests for single step bank transactions list view"""
        context = {
            'form': SingleStepTransactionForm(checker_user=request.user),
            'transactions_list': self.get_queryset()
        }
        if self.request.GET.get('issuer', None) == 'wallets':
            context['wallets'] = True
        if self.request.GET.get("admin_hierarchy", None) != None:
            context['admin_hierarchy'] = self.request.GET.get("admin_hierarchy")
        return render(request, template_name=self.template_name, context=context)

    def post(self, request, *args, **kwargs):
        """Handles POST requests to single step bank transaction"""
        context = {
            'form': SingleStepTransactionForm(request.POST, checker_user=request.user),
            'transactions_list': self.get_queryset(),
            'show_add_form': True
        }
        if self.request.GET.get('issuer', None) == 'wallets':
            context['wallets'] = True

        if context['form'].is_valid():
            form = context['form']
            context = {
                'form': SingleStepTransactionForm(checker_user=request.user),
                'transactions_list': self.get_queryset(),
                'show_pop_up': True
            }
            if self.request.GET.get('issuer', None) == 'wallets':
                context['wallets'] = True
            try:
                data = form.cleaned_data
                payload = {
                    "is_single_step": True,
                    "pin": data["pin"],
                    "user": request.user.username,
                    "amount": str(data["amount"]),
                    "issuer": data["issuer"],
                    "msisdn": data["msisdn"]
                }
                if data["issuer"] in ["orange", "bank_wallet"]:
                    payload["full_name"] = data["full_name"]
                if data["issuer"] == "bank_card":
                    payload["full_name"] = data["creditor_name"]
                    payload["bank_card_number"] = data["creditor_account_number"]
                    payload["bank_code"] =  data["creditor_bank"]
                    payload["bank_transaction_type"] = data["transaction_type"]
                    del payload['msisdn']
                if data["issuer"] == "aman":
                    payload["first_name"] =  data["first_name"]
                    payload["last_name"] =  data["last_name"]
                    payload["email"] =  data["email"]
                http_or_https = "http://" if get_from_env("ENVIRONMENT") == "local" else "https://"
                
                response = requests.post(
                http_or_https + request.get_host() + str(reverse_lazy("instant_api:disburse_single_step")),
                json=payload
            )
                # response = BankTransactionsChannel.send_transaction(single_step_bank_transaction, False)
                data = {
                    "status" : response.json().get('status_code'),
                    "message": response.json().get('status_description')
                }
                return redirect(request.path + '?' + urllib.parse.urlencode(data))
            
            except:
                error_msg = "Process stopped during an internal error, please can you try again."
                data = {
                    "status" : status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": error_msg
                }
                return redirect(request.path + '?' + urllib.parse.urlencode(data))

        return render(request, template_name=self.template_name, context=context)


class DownloadSampleSheetView(UserWithAcceptVFOnboardingPermissionRequired, View):
    """
    View for downloading disbursement sample files
    """

    def generate_e_wallets_sample_file(self):
        """"""
        """Generate e-wallets wallets sample data frame"""
        filename = 'e_wallets_sample_file.xlsx'
        fake = fake_factory.create()
        e_wallets_headers = ['mobile number', 'amount', 'issuer']
        e_wallets_sample_records = []

        for _ in range(9):
            msisdn_carrier = random.choice(['010########', '011########', '012########'])
            msisdn = f"{fake.numerify(text=msisdn_carrier)}"
            amount = round(random.random() * 1000, 2)
            issuer = random.choice(['vodafone', 'etisalat', 'aman'])
            e_wallets_sample_records.append([msisdn, amount, issuer])

        e_wallets_df = pd.DataFrame(e_wallets_sample_records, columns=e_wallets_headers)
        return filename, e_wallets_df

    def generate_bank_wallets_sample_df(self):
        """Generate bank wallets sample data frame"""
        filename = 'bank_wallets_sample_file.xlsx'
        fake = fake_factory.create()
        bank_wallets_headers = ['mobile number', 'amount', 'full name', 'issuer']
        bank_wallets_sample_records = []

        for _ in range(9):
            msisdn_carrier = random.choice(['010########', '011########', '012########'])
            msisdn = f"{fake.numerify(text=msisdn_carrier)}"
            amount = round(random.random() * 1000, 2)
            full_name = f"{fake.first_name()} {fake.last_name()} {fake.first_name()}"
            issuer = random.choice(['orange', 'bank_wallet'])
            bank_wallets_sample_records.append([msisdn, amount, full_name, issuer])

        bank_wallets_df = pd.DataFrame(bank_wallets_sample_records, columns=bank_wallets_headers)
        return filename, bank_wallets_df

    def generate_bank_cards_sample_df(self):
        """Generate bank cards sample data frame"""
        filename = 'bank_cards_sample_file.xlsx'
        fake = fake_factory.create()
        bank_cards_headers = ['account number / IBAN', 'amount', 'full name', 'bank swift code', 'transaction type']
        bank_cards_sample_records = []

        for _ in range(9):
            account_number = f"{fake.numerify(text='#'*random.randint(6, 20))}"
            if _ % 3 == 0:
                account_number = f"{fake.numerify(text='EG'+'#'*random.randint(27, 27))}"
            amount = round(random.random() * 1000, 2)
            full_name = f"{fake.first_name()} {fake.last_name()} {fake.first_name()}"
            bank_code = random.choice(VALID_BANK_CODES_LIST)
            transaction_type = random.choice(VALID_BANK_TRANSACTION_TYPES_LIST).lower()
            bank_cards_sample_records.append([account_number, amount, full_name, bank_code, transaction_type])

        bank_cards_df = pd.DataFrame(bank_cards_sample_records, columns=bank_cards_headers)
        return filename, bank_cards_df

    def get(self, request, *args, **kwargs):
        """Handles GET requests calls to download the sheet"""
        file_type = request.GET.get("type", None)

        try:
            # 1. Generate data frame based on the given type
            if file_type == 'bank_wallets':
                filename, file_df = self.generate_bank_wallets_sample_df()
            elif file_type == 'bank_cards':
                filename, file_df = self.generate_bank_cards_sample_df()
            elif file_type == 'e_wallets':
                filename, file_df = self.generate_e_wallets_sample_file()
            else:
                raise Http404

            # 2. Save data frame as an excel file into memory for streaming
            in_memory_fp = io.BytesIO()
            file_df.to_excel(in_memory_fp, index=False)
            in_memory_fp.seek(0)

            # 3. Return the excel file as an attachment to be downloaded
            response = HttpResponse(
                    in_memory_fp.read(),
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response['Content-Disposition'] = f'attachment; filename={filename}'
            in_memory_fp.close()

            return response
        except:
            raise Http404


class ExportClientsTransactionsMonthlyReport:
    """
    class for export clients transactions monthly reports.
    """
    def __init__(self):
        self.superadmin_user = None
        self.superadmins = None
        self.start_date = None
        self.end_date = None
        self.first_day = None
        self.last_day = None
        self.instant_or_accept_perm = False
        self.vf_facilitator_perm = False
        self.default_vf__or_bank_perm = False

    def refine_first_and_end_date_format(self):
        """
        Refine start date and end date format using datetime and set values for first and last days.
        make_aware(): Converts naive datetime object (without timezone info) to the one that has timezone info,
            using timezone specified in your django settings if you don't specify it explicitly as a second argument.
        """
        first_day = datetime(
                year=int(self.start_date.split('-')[0]),
                month=int(self.start_date.split('-')[1]),
                day=int(self.start_date.split('-')[2]),
        )
        self.first_day = make_aware(first_day)

        last_day = datetime(
                year=int(self.end_date.split('-')[0]),
                month=int(self.end_date.split('-')[1]),
                day=int(self.end_date.split('-')[2]),
                hour=23,
                minute=59,
                second=59,
        )
        self.last_day = make_aware(last_day)

    def _customize_issuer_in_qs_values(self, qs):
        """Append admin username to the output transactions queryset values dict"""
        for q in qs:
            if len(str(q['issuer'])) > 20:
                q['issuer'] = 'C'
            elif q['issuer'] != AbstractBaseIssuer.BANK_WALLET and len(q['issuer']) == 1:
                q['issuer'] = str(dict(AbstractBaseIssuer.ISSUER_TYPE_CHOICES)[q['issuer']]).lower()

        return qs

    def _calculate_and_add_fees_to_qs_values(self, qs, failed_qs=False):
        """Calculate and append the fees to the output transactions queryset values dict"""
        for q in qs:
            if failed_qs and q['issuer'] in ['vodafone', 'etisalat', 'aman']:
                q['fees'], q['vat'] = 0, 0
            elif failed_qs and q.__class__.__name__ == 'InstantTransaction' \
                    and q.issuer_type in ['orange', 'bank_wallet'] and BankTransaction.objects.filter(
                    status=AbstractBaseStatus.PENDING,
                    end_to_end=q.uid
            ).count() == 0:
                q['fees'], q['vat'] = 0, 0
            else:
                q['fees'], q['vat'] = Budget.objects.get(disburser__username=q['admin']). \
                    calculate_fees_and_vat_for_amount(q['total'], q['issuer'], q['count'])
        return qs

    def _add_issuers_with_values_0_to_final_data(self, final_data, issuers_exist):
        for key in final_data.keys():
            for el in final_data[key]:
                if el['issuer'] != 'total':
                    issuers_exist[el['issuer']] = True
            for issuer in issuers_exist.keys():
                if not issuers_exist[issuer]:
                    default_issuer_dict = {'issuer': issuer, 'count': 0, 'total': 0}
                    if self.instant_or_accept_perm:
                        default_issuer_dict['fees'] = 0
                        default_issuer_dict['vat'] = 0
                    final_data[key].append(default_issuer_dict)
                issuers_exist[issuer] = False

        return final_data

    def _annotate_vf_ets_aman_qs(self, qs):
        """ Annotate qs then add admin username to qs"""
        if self.vf_facilitator_perm:
            qs = qs.annotate(
                    admin=F('doc__disbursed_by__root__username'),
                    vf_identifier=F('doc__disbursed_by__root__client__vodafone_facilitator_identifier')
            ).values('admin', 'issuer', 'vf_identifier'). \
                annotate(total=Sum('amount'), count=Count('id'))
        else:
            qs = qs.annotate(admin=F('doc__disbursed_by__root__username')).values('admin', 'issuer'). \
                annotate(total=Sum('amount'), count=Count('id'))
        return self._customize_issuer_in_qs_values(qs)

    def _annotate_instant_trxs_qs(self, qs):
        """ Annotate qs then add admin username to qs"""
        qs = qs.annotate(
                admin=Case(
                        When(from_user__isnull=False, then=F('from_user__root__username')),
                        default=F('document__disbursed_by__root__username')
                )
        ).extra(select={'issuer': 'issuer_type'}).values('admin', 'issuer'). \
            annotate(total=Sum('amount'), count=Count('uid'))
        return self._customize_issuer_in_qs_values(qs)

    def aggregate_vf_ets_aman_transactions(self):
        """Calculate vodafone, etisalat, aman transactions details from DisbursementData model"""
        if self.status == 'failed':
            qs = DisbursementData.objects.filter(
                    Q(disbursed_date__gte=self.first_day),
                    Q(disbursed_date__lte=self.last_day),
                    ~Q(reason__exact=''),
                    Q(is_disbursed=False),
                    Q(doc__disbursed_by__root__client__creator__in=self.superadmins)
            )
        elif self.status == 'success':
            qs = DisbursementData.objects.filter(
                    Q(disbursed_date__gte=self.first_day),
                    Q(disbursed_date__lte=self.last_day),
                    Q(is_disbursed=True),
                    Q(doc__disbursed_by__root__client__creator__in=self.superadmins)
            )
        else:
            qs = DisbursementData.objects.filter(
                    Q(disbursed_date__gte=self.first_day),
                    Q(disbursed_date__lte=self.last_day),
                    (Q(is_disbursed=True) | (~Q(reason__exact='') & Q(is_disbursed=False))),
                    Q(doc__disbursed_by__root__client__creator__in=self.superadmins)
            )
        if self.status in ['success', 'failed']:
            qs = self._annotate_vf_ets_aman_qs(qs)
            if self.instant_or_accept_perm:
                qs = self._calculate_and_add_fees_to_qs_values(qs, self.status == 'failed')
            return qs

        # handle if status is all
        # divide qs into success and failed
        failed_qs = qs.filter(~Q(reason__exact='') & Q(is_disbursed=False))
        # annotate failed qs and add admin username
        failed_qs = self._annotate_vf_ets_aman_qs(failed_qs)

        success_qs = qs.filter(Q(is_disbursed=True))
        # annotate success qs and add admin username
        success_qs = self._annotate_vf_ets_aman_qs(success_qs)

        if self.instant_or_accept_perm:
            # calculate fees and vat for failed qs
            failed_qs = self._calculate_and_add_fees_to_qs_values(failed_qs, True)
            # calculate fees and vat for success qs
            success_qs = self._calculate_and_add_fees_to_qs_values(success_qs)
        return [*failed_qs, *success_qs]

    def aggregate_bank_wallets_orange_instant_transactions(self):
        """Calculate bank wallets, orange, instant transactions details from InstantTransaction model"""
        if self.status == 'failed':
            qs = InstantTransaction.objects.filter(
                    Q(disbursed_date__gte=self.first_day),
                    Q(disbursed_date__lte=self.last_day),
                    Q(status=AbstractBaseStatus.FAILED),
                    (Q(document__disbursed_by__root__client__creator__in=self.superadmins) |
                    Q(from_user__root__client__creator__in=self.superadmins))
            )
        elif self.status == 'success':
            qs = InstantTransaction.objects.filter(
                    Q(disbursed_date__gte=self.first_day),
                    Q(disbursed_date__lte=self.last_day),
                    Q(status=AbstractBaseStatus.SUCCESSFUL),
                    (Q(document__disbursed_by__root__client__creator__in=self.superadmins) |
                    Q(from_user__root__client__creator__in=self.superadmins))
            )
        else:
            qs = InstantTransaction.objects.filter(
                    Q(disbursed_date__gte=self.first_day),
                    Q(disbursed_date__lte=self.last_day),
                    Q(status__in=[AbstractBaseStatus.SUCCESSFUL,
                                  AbstractBaseStatus.PENDING,
                                  AbstractBaseStatus.FAILED]),
                    ~Q(transaction_status_code__in=['500', '424']),
                    (Q(document__disbursed_by__root__client__creator__in=self.superadmins) |
                    Q(from_user__root__client__creator__in=self.superadmins))
            )
        if self.status in ['success', 'failed']:
            qs = self._annotate_instant_trxs_qs(qs)
            qs = self._calculate_and_add_fees_to_qs_values(qs, self.status == 'failed')
            return qs

        # handle if status is all
        # divide qs into success and failed and pending
        failed_qs = qs.filter(Q(status=AbstractBaseStatus.FAILED))
        # annotate failed qs and add admin username
        failed_qs = self._annotate_instant_trxs_qs(failed_qs)

        success_qs = qs.filter(Q(status__in=[
            AbstractBaseStatus.SUCCESSFUL,
            AbstractBaseStatus.PENDING
        ]))
        # annotate success qs and add admin username
        success_qs = self._annotate_instant_trxs_qs(success_qs)

        # calculate fees and vat for failed qs
        failed_qs = self._calculate_and_add_fees_to_qs_values(failed_qs, True)
        # calculate fees and vat for success qs
        success_qs = self._calculate_and_add_fees_to_qs_values(success_qs)
        return [*failed_qs, *success_qs]

    def aggregate_bank_cards_transactions(self):
        """Calculate bank cards transactions details from BankTransaction model"""
        if self.status == 'failed':
            qs_ids = BankTransaction.objects.filter(
                    Q(disbursed_date__gte=self.first_day),
                    Q(disbursed_date__lte=self.last_day),
                    Q(status=AbstractBaseACHTransactionStatus.FAILED),
                    Q(end_to_end=""),
                    (Q(document__disbursed_by__root__client__creator__in=self.superadmins) |
                    Q(user_created__root__client__creator__in=self.superadmins))
            ).order_by("parent_transaction__transaction_id", "-id"). \
                distinct("parent_transaction__transaction_id").values('id')
        elif self.status == 'success':
            qs_ids = BankTransaction.objects.filter(
                    Q(disbursed_date__gte=self.first_day),
                    Q(disbursed_date__lte=self.last_day),
                    Q(status=AbstractBaseACHTransactionStatus.SUCCESSFUL),
                    Q(end_to_end=""),
                    (Q(document__disbursed_by__root__client__creator__in=self.superadmins) |
                    Q(user_created__root__client__creator__in=self.superadmins))
            ).order_by("parent_transaction__transaction_id", "-id"). \
                distinct("parent_transaction__transaction_id").values('id')
        else:
            qs_ids = BankTransaction.objects.filter(
                    Q(disbursed_date__gte=self.first_day),
                    Q(disbursed_date__lte=self.last_day),
                    Q(end_to_end=""),
                    Q(status__in=[AbstractBaseACHTransactionStatus.PENDING, AbstractBaseACHTransactionStatus.SUCCESSFUL, AbstractBaseACHTransactionStatus.RETURNED]),
                    (Q(document__disbursed_by__root__client__creator__in=self.superadmins) |
                    Q(user_created__root__client__creator__in=self.superadmins))
            ).order_by("parent_transaction__transaction_id", "-id"). \
                distinct("parent_transaction__transaction_id").values('id')
        qs = BankTransaction.objects.filter(id__in=qs_ids).annotate(
                admin=Case(
                        When(document__disbursed_by__isnull=False, then=F('document__disbursed_by__root__username')),
                        default=F('user_created__root__username')
                )
        ).extra(select={'issuer': 'transaction_id'}).values('admin', 'issuer'). \
            annotate(total=Sum('amount'), count=Count('id'))

        qs = self._customize_issuer_in_qs_values(qs)
        qs = self._calculate_and_add_fees_to_qs_values(qs)
        return qs

    def group_result_transactions_data(self, vf_ets_aman_qs, bank_wallets_orange_instant_qs, cards_qs):
        """Group all data by admin"""
        transactions_details_list = [vf_ets_aman_qs, bank_wallets_orange_instant_qs, cards_qs]
        final_data = dict()

        for transactions_result_type in transactions_details_list:
            for q in transactions_result_type:
                if q['admin'] in final_data:
                    issuer_exist = False
                    for admin_q in final_data[q['admin']]:
                        if q['issuer'] == admin_q['issuer']:
                            admin_q['total'] += q['total']
                            admin_q['count'] += q['count']
                            if self.instant_or_accept_perm:
                                admin_q['fees'] += q['fees']
                                admin_q['vat'] += q['vat']
                            issuer_exist = True
                            break
                    if not issuer_exist:
                        final_data[q['admin']].append(q)
                else:
                    final_data[q['admin']] = [q]

        return final_data

    def write_data_to_excel_file(self, final_data, column_names_list, distinct_msisdn=None):
        """Write exported transactions data to excel file"""
        filename = _(f"clients_monthly_report_{self.status}_{self.start_date}_{self.end_date}_{randomword(4)}.xls")
        file_path = f"{settings.MEDIA_ROOT}/documents/disbursement/{filename}"
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('report')

        # 1. Write sheet header/column names - first row
        row_num = 0
        font_style = xlwt.XFStyle()
        font_style.font.bold = True

        for col_nums in range(len(column_names_list)):
            ws.write(row_num, col_nums, column_names_list[col_nums], font_style)

        # 2. Write sheet body/data - remaining rows
        font_style = xlwt.XFStyle()
        row_num += 1

        if self.instant_or_accept_perm or self.default_vf__or_bank_perm:
            col_nums = {
                'total': 2,
                'vodafone': 3,
                'etisalat': 4,
                'aman': 5,
                'orange': 6,
                'B': 7,
                'C': 8
            }
            if self.default_vf__or_bank_perm:
                col_nums['default']= 9

            for key in final_data.keys():
                ws.write(row_num, 0, key, font_style)
                ws.write(row_num, 1, 'Volume', font_style)
                ws.write(row_num+1, 1, 'Count', font_style)
                if self.instant_or_accept_perm:
                    ws.write(row_num+2, 1, 'Fees', font_style)
                    ws.write(row_num+3, 1, 'Vat', font_style)

                for el in final_data[key]:
                    ws.write(row_num, col_nums[el['issuer']], el['total'], font_style)
                    ws.write(row_num+1, col_nums[el['issuer']], el['count'], font_style)
                    if self.instant_or_accept_perm:
                        ws.write(row_num+2, col_nums[el['issuer']], el['fees'], font_style)
                        ws.write(row_num+3, col_nums[el['issuer']], el['vat'], font_style)
                if self.instant_or_accept_perm:
                    row_num += 4
                else:
                    row_num += 2
        else:
            for key in final_data.keys():
                current_admin_report = final_data[key][0]
                ws.write(row_num, 0, key, font_style)
                ws.write(row_num, 1, current_admin_report['count'], font_style)
                ws.write(row_num, 2, current_admin_report['total'], font_style)
                ws.write(row_num, 3, len(distinct_msisdn[key]), font_style)
                ws.write(row_num, 4, current_admin_report['full_date'], font_style)
                ws.write(row_num, 5, current_admin_report['vf_facilitator_identifier'], font_style)
                row_num += 1

        wb.save(file_path)
        report_download_url = f"{settings.BASE_URL}{str(reverse('disbursement:download_exported'))}?filename={filename}"
        return report_download_url

    def prepare_transactions_report(self):
        """Prepare report for transactions related to client"""
        # 1. Format start and end date
        self.refine_first_and_end_date_format()

        # 2. Prepare current super admins
        if not self.superadmins:
            self.superadmins = [self.superadmin_user]

        # validate that all super admins have (instant || accept) or vf facilitator permission
        for super_admin in self.superadmins:
            if super_admin.is_instant_model_onboarding or \
                    super_admin.is_accept_vodafone_onboarding:
                self.instant_or_accept_perm = True
            elif super_admin.is_vodafone_facilitator_onboarding:
                self.vf_facilitator_perm = True
            else:
                self.default_vf__or_bank_perm = True
        onboarding_array = [self.vf_facilitator_perm, self.instant_or_accept_perm, self.default_vf__or_bank_perm]
        if not (onboarding_array.count(True) == 1 and onboarding_array.count(False) == 2):
            return False

        # 3. Calculate vodafone, etisalat, aman transactions details
        vf_ets_aman_qs = self.aggregate_vf_ets_aman_transactions()

        bank_wallets_orange_instant_transactions_qs = []
        bank_cards_transactions_qs = []

        if self.instant_or_accept_perm:
            # 5. Calculate bank wallets, orange, instant transactions details
            bank_wallets_orange_instant_transactions_qs = self.aggregate_bank_wallets_orange_instant_transactions()

            # 6. Calculate bank cards/accounts transactions details
            bank_cards_transactions_qs = self.aggregate_bank_cards_transactions()

        # 4. Group all data by admin
        final_data = self.group_result_transactions_data(
                vf_ets_aman_qs, bank_wallets_orange_instant_transactions_qs, bank_cards_transactions_qs
        )

        if self.instant_or_accept_perm  or self.default_vf__or_bank_perm:
            # 5. Calculate total volume, count, fees for each admin
            for key in final_data.keys():
                total_per_admin = {
                    'admin': key,
                    'issuer': 'total',
                    'total': round(Decimal(0), 2),
                    'count': round(Decimal(0), 2),
                }
                if self.instant_or_accept_perm:
                    total_per_admin['fees'] = round(Decimal(0), 2)
                    total_per_admin['vat'] = round(Decimal(0), 2)

                for el in final_data[key]:
                    total_per_admin['total'] += round(Decimal(el['total']), 2)
                    total_per_admin['count'] += el['count']
                    if self.instant_or_accept_perm:
                        total_per_admin['fees'] += el['fees']
                        total_per_admin['vat'] += el['vat']
                final_data[key].append(total_per_admin)

        # 6. Add issuer with values 0 to final data
        if self.vf_facilitator_perm:
            issuers_exist = {
                'default': False,
            }
        else:
            issuers_exist = {
                'vodafone': False,
                'etisalat': False,
                'aman': False,
                'orange': False,
                'B': False,
                'C': False
            }
            if self.default_vf__or_bank_perm:
                issuers_exist['default'] = False


        final_data = self._add_issuers_with_values_0_to_final_data(final_data, issuers_exist)

        # 7. Add all admin that have no transactions
        admins_qs = []
        for super_admin in self.superadmins:
            admins_qs = [*admins_qs, *super_admin.children()]
        for current_admin in admins_qs:
            if not current_admin.username in final_data.keys():
                if self.vf_facilitator_perm:
                    final_data[current_admin.username] = [{
                        **DEFAULT_PER_ADMIN_FOR_VF_FACILITATOR_TRANSACTIONS_REPORT,
                        'full_date': f"{self.start_date} to {self.end_date}",
                        'vf_facilitator_identifier': current_admin.client.vodafone_facilitator_identifier
                    }]
                elif self.instant_or_accept_perm:
                    final_data[current_admin.username] = DEFAULT_LIST_PER_ADMIN_FOR_TRANSACTIONS_REPORT
                else:
                    final_data[current_admin.username] = DEFAULT_LIST_PER_ADMIN_FOR_TRANSACTIONS_REPORT_raseedy_vf

        if self.vf_facilitator_perm:
            # 8. calculate distinct msisdn per admin
            distinct_msisdn = dict()
            for el in vf_ets_aman_qs.values():
                if el['admin'] in distinct_msisdn:
                    distinct_msisdn[el['admin']].add(el['msisdn'])
                else:
                    distinct_msisdn[el['admin']] = set([el['msisdn']])

            # 9. Add all admin that have no transactions to distinct msisdn
            for current_admin in admins_qs:
                if not current_admin.username in distinct_msisdn.keys():
                    distinct_msisdn[current_admin.username] = set([])

            column_names_list = [
                'Account Name ', 'Total Count', 'Total Amount', 'Distinct Receivers', 'Full Date', 'Billing Number'
            ]
            return self.write_data_to_excel_file(final_data, column_names_list, distinct_msisdn)
        else:
            column_names_list = [
                'Clients', '', 'Total', 'Vodafone', 'Etisalat', 'Aman', 'Orange', 'Bank Wallets', 'Bank Accounts/Cards'
            ]
            if self.default_vf__or_bank_perm:
                column_names_list.append('Default')

            # 10. Write final data to excel file
            return self.write_data_to_excel_file(final_data, column_names_list)

    def run(self, user_id, start_date, end_date, status, super_admins_ids=[]):
        self.superadmin_user = User.objects.get(id=user_id)
        self.start_date = start_date
        self.end_date = end_date
        self.status = status
        self.instant_or_accept_perm = False
        self.vf_facilitator_perm = False
        self.default_vf__or_bank_perm = False
        self.superadmins = User.objects.filter(pk__in=super_admins_ids)
        report_download_url = self.prepare_transactions_report()

        return report_download_url
    