import logging

import requests

from decimal import Decimal

from django import forms
from django.forms import modelformset_factory
from django.utils.translation import gettext as _

from payouts.utils import get_dot_env
from users.tasks import set_pin_error_mail
from users.models.base_user import User

from .models import Agent, VMTData, BankTransaction
from .utils import BANK_CODES, VALID_BANK_TRANSACTION_TYPES_LIST,\
    VALID_BANK_CODES_LIST, determine_trx_category_and_purpose
from instant_cashin.utils import get_from_env, get_digits

WALLET_API_LOGGER = logging.getLogger("wallet_api")

MSG_TRY_OR_CONTACT = "can you try again or contact you support team"
MSG_PIN_SETTING_ERROR = _(f"Set pin process stopped during an internal error, {MSG_TRY_OR_CONTACT}")


class VMTDataForm(forms.ModelForm):
    class Meta:
        model = VMTData
        exclude = ('vmt', 'vmt_environment')

    def __init__(self, *args, root, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = root

    def save(self, commit=True):
        vmt = super().save(commit=False)
        vmt.vmt_environment = 'PRODUCTION'
        vmt.vmt = self.root
        vmt.save()
        return vmt


class AgentForm(forms.ModelForm):
    """
    Agent form for adding new agents for newly created Admins
    """
    msisdn = forms.CharField(max_length=11, min_length=11, label=_("Mobile number"))

    class Meta:
        model = Agent
        fields = ('msisdn',)

    def __init__(self, *args, root, **kwargs):
        self.root = root
        super().__init__(*args, **kwargs)

    def clean_msisdn(self):
        """
        :return: Validate the passed agent mobile number against r regex (EG, 010x, 011x, 012x)
        """
        msisdn = self.cleaned_data.get('msisdn', None)
        if not msisdn:
            return msisdn
        import re
        r = re.compile('(201|01)[0-2|5]\d{7}')
        if not r.match(msisdn):
            raise forms.ValidationError(_("Mobile number is not valid"))
        return msisdn


class PinForm(forms.Form):
    """
    Pin form used by Admin to set a new pin for his/her own superagent and agent(s)
    """
    pin = forms.CharField(
            required=True,
            max_length=6,
            min_length=6,
            widget=forms.PasswordInput(attrs={'size': 6, 'maxlength': 6, 'placeholder': _('Add new pin')})
    )

    def __init__(self, *args, root, **kwargs):
        self.root = root
        super().__init__(*args, **kwargs)
        if self.root.is_vodafone_default_onboarding:
            self.agents = Agent.objects.filter(wallet_provider=root)
        else:
            self.agents = Agent.objects.filter(wallet_provider=root.super_admin)
        self.env = get_dot_env()

    def get_form(self):
        agent = self.agents.first()
        if self.root.is_vodafone_default_onboarding and agent and agent.pin:
            return None
        return self

    def clean_pin(self):
        """
        :return: Validate that pin is a valid number
        """
        pin = self.cleaned_data.get('pin')

        if pin and not pin.isnumeric():
            raise forms.ValidationError(_("Pin must be numeric"))
        return pin

    def set_pin(self):
        raw_pin = self.cleaned_data.get('pin')
        if not raw_pin:
            return False
        if self.root.is_vodafone_default_onboarding and self.root.callwallets_moderator.first().set_pin:
            msisdns = list(self.agents.values_list('msisdn', flat=True))
            transactions, error = self.call_wallet(raw_pin, msisdns)
            if error:
                self.add_error('pin', error)
                return False
            error = self.get_transactions_error(transactions)       # handle transactions list
            if error:
                self.add_error('pin', error)
                return False

        self.agents.update(pin=True)
        self.root.set_pin(raw_pin)
        return True

    def call_wallet(self, pin, msisdns):
        superadmin = self.root.client.creator
        payload = superadmin.vmt.accumulate_set_pin_payload(msisdns, pin)
        try:
            WALLET_API_LOGGER.debug(f"[request] [SET PIN] [{self.root}] -- {payload['USERS']}")
            response = requests.post(self.env.str(superadmin.vmt.vmt_environment), json=payload, verify=False)
        except Exception as e:
            WALLET_API_LOGGER.debug(f"[message] [SET PIN ERROR] [{self.root}] -- {e.args}")
            return None, MSG_PIN_SETTING_ERROR
        else:
            WALLET_API_LOGGER.debug(f"[response] [SET PIN] [{self.root}] -- {str(response.text)}")

        if response.ok:
            response_dict = response.json()
            transactions = response_dict.get('TRANSACTIONS', None)
            if not transactions:
                error_message = response_dict.get('MESSAGE', None) or _("Failed to set pin")
                return None, error_message
            return transactions, None
        return None, MSG_PIN_SETTING_ERROR

    def get_transactions_error(self, transactions):
        failed_trx = list(filter(lambda trx: trx['TXNSTATUS'] != "200", transactions))

        if failed_trx:
            error_message = MSG_PIN_SETTING_ERROR
            for agent_index in range(len(failed_trx)):
                if failed_trx[agent_index]['TXNSTATUS'] == "407":
                    error_message = failed_trx[agent_index]['MESSAGE']
                    break

                elif failed_trx[agent_index]['TXNSTATUS'] == "608":
                    error_message = "Pin has been already registered for those agents. For assistance call 7001"
                    break

                elif failed_trx[agent_index]['TXNSTATUS'] == "1661":
                    error_message = "You cannot use an old PIN. For assistance call 7001"
                    break

            set_pin_error_mail.delay(self.root.id)
            return error_message

        return None


class BalanceInquiryPinForm(forms.Form):
    """
    Pin form for balance inquiry done by Admin users
    """
    pin = forms.CharField(
            required=True,
            min_length=6,
            max_length=6,
            widget=forms.PasswordInput(attrs={'size': 6, 'maxlength': 6, 'placeholder': _('Enter pin')})
    )

    def clean_pin(self):
        """
        :return: Validate that pin is a valid number
        """
        pin = self.cleaned_data.get('pin')

        if pin and not pin.isnumeric():
            raise forms.ValidationError(_("Pin must be numeric"))
        return pin


class SingleStepTransactionForm(forms.ModelForm):
    """
    single step transaction Form by Checker users
    """
    pin = forms.CharField(
        required=True,
        min_length=6,
        max_length=6,
        widget=forms.PasswordInput(attrs={
            'class': "form-control", 'id': "pin",
            'name': "pin", 'placeholder': "Enter Pin"})
    )
    transaction_type = forms.CharField(
        required=True,
        widget=forms.Select(choices=((trx_type, trx_type.replace('_', ' ').capitalize()) for trx_type in VALID_BANK_TRANSACTION_TYPES_LIST) , attrs={
            'class': "form-control", 'id': "trx_type", 'name': "trx_type"
        })
    )

    class Meta:
        model = BankTransaction
        fields = ('creditor_account_number', 'amount', 'creditor_name', 'creditor_bank')

    def __init__(self, *args, current_user, **kwargs):
        self.current_user = current_user
        super(SingleStepTransactionForm, self).__init__(*args, **kwargs)
        self.fields['creditor_account_number'].widget.attrs.update({
            'class': "form-control", 'id': "accountNumber",
            'name': "accountNumber", 'placeholder': "Enter Account Number"
        })
        self.fields['amount'].widget.attrs.update({
            'class': "form-control", 'id': "trxAmount", 'min': 30,
            'name': "trxAmount", 'placeholder': "Enter Transaction Amount"
        })
        self.fields['creditor_name'].widget.attrs.update({
            'class': "form-control", 'id': "full_name",
            'name': "full_name", 'placeholder': "Enter Full Name"
        })
        bank_choices = ((dic['code'], dic['name']) for dic in BANK_CODES)
        self.fields['creditor_bank'].widget = forms.Select(choices=bank_choices, attrs={
            'class': "form-control", 'id': "bank_name", 'name': "bank_name"
        })

    def clean(self):
        cleaned_data = super(SingleStepTransactionForm, self).clean()

        # validate account number
        creditor_account_number = cleaned_data.get('creditor_account_number')
        account = get_digits(str(creditor_account_number))
        if not (account and len(account) == 16):
            self.add_error('creditor_account_number', "Invalid Account number")

        # validate amount
        amount = cleaned_data.get('amount')
        if not (str(amount).replace('.', '', 1).isdigit() and Decimal(amount) >= 1.0):
            self.add_error('amount', "Invalid amount")

        # validate for empty names
        creditor_name = cleaned_data.get('creditor_name')
        if not creditor_name:
            self.add_error('creditor_name', "Invalid name")

        # validate bank codes
        creditor_bank = cleaned_data.get('creditor_bank')
        if not creditor_bank or str(creditor_bank).upper() not in VALID_BANK_CODES_LIST:
            self.add_error('creditor_bank', "Invalid bank code")

        # validate transaction type
        transaction_type = cleaned_data.get('transaction_type')
        if not transaction_type or str(transaction_type).upper() not in VALID_BANK_TRANSACTION_TYPES_LIST:
            self.add_error('transaction_type', "Invalid transaction purpose")

        # validate pin
        pin = cleaned_data.get('pin')
        if pin and not pin.isnumeric():
            self.add_error('pin', "Pin must be numeric")
        if self.current_user.root.pin and not self.current_user.root.check_pin(pin):
            self.add_error('pin', "Invalid Pin")
        return cleaned_data

    def save(self, commit=True):
        category_purpose_dict = determine_trx_category_and_purpose(self.cleaned_data.get('transaction_type'))
        del self.cleaned_data['transaction_type']

        single_step_bank_transaction = super().save(commit=False)

        single_step_bank_transaction.user_created = self.current_user
        single_step_bank_transaction.amount = round(Decimal(single_step_bank_transaction.amount), 2)
        single_step_bank_transaction.currency = "EGP"
        single_step_bank_transaction.debtor_address_1 = "EG"
        single_step_bank_transaction.creditor_address_1 = "EG"
        single_step_bank_transaction.corporate_code = get_from_env("ACH_CORPORATE_CODE")
        single_step_bank_transaction.debtor_account = get_from_env("ACH_DEBTOR_ACCOUNT")
        single_step_bank_transaction.category_code = category_purpose_dict.get("category_code", "CASH")
        single_step_bank_transaction.purpose = category_purpose_dict.get("purpose", "CASH")
        single_step_bank_transaction.is_single_step = True

        single_step_bank_transaction.save()
        return single_step_bank_transaction


AgentFormSet = modelformset_factory(model=Agent, form=AgentForm, min_num=1, validate_min=True, can_delete=True, extra=0)
