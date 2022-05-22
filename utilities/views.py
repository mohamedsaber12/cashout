# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
import logging

from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.generic import UpdateView, View

from data.utils import randomword
from payouts import settings
from users.mixins import (MakeTransferRequestPermissionRequired,
                          SuperOwnsCustomizedBudgetClientRequiredMixin)

from .forms import BudgetModelForm, IncreaseBalanceRequestForm
from .mixins import BudgetActionMixin
from .models import Budget
from .tasks import send_transfer_request_email
from utilities.models import TopupRequest, TopupAction

BUDGET_LOGGER = logging.getLogger("custom_budgets")


class BudgetUpdateView(SuperOwnsCustomizedBudgetClientRequiredMixin,
                       BudgetActionMixin,
                       UpdateView):
    """
    View for enabling SuperAdmin users to update and maintain custom Root budgets
    """
    model = Budget
    form_class = BudgetModelForm
    template_name = 'utilities/budget.html'
    context_object_name = 'budget_object'
    success_message = _("Budget updated successfully!")
    failure_message = _("Adding new budget failure, check below errors and try again!")

    def get_object(self, queryset=None):
        """Retrieve the budget object of the accessed disburser"""
        return get_object_or_404(Budget, disburser__username=self.kwargs["username"])


class IncreaseBalanceRequestView(MakeTransferRequestPermissionRequired, View):
    """
    Request view for increase balance on accept vodafone admins
    """
    template_name = 'utilities/transfer_request.html'

    def get(self, request, *args, **kwargs):
        """Handles GET requests for Increase Balance Request"""
        context = {
            'request_received': False,
            'form': IncreaseBalanceRequestForm(),
        }
        return render(request, template_name=self.template_name, context=context)

    def post(self, request, *args, **kwargs):
        """Handles POST requests increase balance request"""
        context = {
            'form': IncreaseBalanceRequestForm(request.POST, request.FILES),
        }

        if context['form'].is_valid():
            form = context['form']
            BUDGET_LOGGER.debug(
                f"[message] [transfer request] [{request.user}] -- payload: {form.cleaned_data}"
            )
            # Prepare email message
            message = _(f"""Dear All,<br><br>
            <label>Admin Username:       </label> {request.user}<br/>
            <label>Admin E-mail:         </label> {request.user.email}<br/>
            <label>Request Date/Time:    </label> {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}<br/>
            <label>Amount To Be Added:   </label>{form.cleaned_data['amount']}<br/>
            <label>Transfer Type:        </label> {form.cleaned_data['type'].replace("_", " ")} <br/>
            <label>Currency:             </label> {form.cleaned_data['currency'].replace("_", " ")} <br/><br/>
            """)

            if form.cleaned_data['type'] == 'from_accept_balance':
                rest_of_message = _(
                        f"<label>Accept username:  </label> {form.cleaned_data['username']} <br/><br/>Best Regards,"
                )
            elif form.cleaned_data['type'] == 'from_bank_transfer':
                rest_of_message = _(f"""<h4>From: </h4>
                <label> Bank Name:  </label> {form.cleaned_data['from_bank']} <br/>
                <label> Account Number:  </label> {form.cleaned_data['from_account_number']} <br/>
                <label> Account Name:  </label> {form.cleaned_data['from_account_name']} <br/>
                <label> Date: </label> {form.cleaned_data['from_date']} <br/><br/>
                <h4>To: </h4>
                <label> Bank Name:  </label> {form.cleaned_data['to_bank']} <br/>
                <label> Account Number:  </label> {form.cleaned_data['to_account_number']} <br/>
                <label> Account Name:  </label> {form.cleaned_data['to_account_name']} <br/><br/>
                Best Regards,""")
            elif form.cleaned_data['type'] == 'from_bank_deposit':
                rest_of_message = _(f"""<h4>From: </h4>
                <label> Depositor:  </label> {form.cleaned_data['from_account_name']} <br/>
                <label> Date: </label> {form.cleaned_data['from_date']} <br/><br/>
                <h4>To: </h4>
                <label> Bank Name:  </label> {form.cleaned_data['to_bank']} <br/>
                <label> Account Number:  </label> {form.cleaned_data['to_account_number']} <br/>
                <label> Account Name:  </label> {form.cleaned_data['to_account_name']} <br/><br/>
                Best Regards,""")
            message += rest_of_message
            file_path = ""

            if form.cleaned_data['type'] == 'from_accept_balance':
                send_transfer_request_email.delay(request.user.username, message)
            else:
                # Save attached file to media and get it's url
                proof_image = request.FILES['to_attach_proof']
                file_path = f"{settings.MEDIA_ROOT}/transfer_request_attach/{randomword(5)}_{proof_image.name}"
                file_name = default_storage.save(file_path, proof_image)
                send_transfer_request_email.delay(request.user.username, message, file_name)
            # save topup information
            TopupRequest.objects.create(
                client=request.user.root,
                amount=form.cleaned_data['amount'],
                currency=form.cleaned_data['currency'],
                transfer_type=form.cleaned_data['type'],
                username=form.cleaned_data['username'],
                from_bank=form.cleaned_data['from_bank'],
                to_bank=form.cleaned_data['to_bank'],
                from_account_number=form.cleaned_data['from_account_number'],
                to_account_number=form.cleaned_data['to_account_number'],
                from_account_name=form.cleaned_data['from_account_name'],
                to_account_name=form.cleaned_data['to_account_name'],
                from_date=form.cleaned_data['from_date'],
                to_attach_proof=file_path,
            )

            context = {
                'request_received': True,
                'form': IncreaseBalanceRequestForm(),
            }
        return render(request, template_name=self.template_name, context=context)



class ListIncreaseBalanceRequestView(MakeTransferRequestPermissionRequired, View):
    template_name = 'utilities/list_transfer_request.html'

    def get(self, request, *args, **kwargs):
        context = {
            'transfer_requests': TopupAction.objects.filter(client=request.user.root),
        }
        return render(request, template_name=self.template_name, context=context)