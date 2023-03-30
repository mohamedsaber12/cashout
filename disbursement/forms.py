import logging
from decimal import Decimal

import phonenumbers
import requests
from django import forms
from django.core.validators import MinValueValidator
from django.forms import modelformset_factory
from django.utils.translation import gettext as _
from phonenumber_field.phonenumber import PhoneNumber

from instant_cashin.utils import get_digits, get_from_env
from payouts.utils import get_dot_env
from users.models import Client
from users.tasks import set_pin_error_mail

from .models import Agent, VMTData
from .utils import (BANK_CODES, VALID_BANK_CODES_LIST,
                    VALID_BANK_TRANSACTION_TYPES_LIST,
                    determine_trx_category_and_purpose)

WALLET_API_LOGGER = logging.getLogger("wallet_api")

MSG_TRY_OR_CONTACT = "can you try again or contact you support team"
MSG_PIN_SETTING_ERROR = _(
    f"Set pin process stopped during an internal error, {MSG_TRY_OR_CONTACT}"
)


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

    msisdn = forms.CharField(
        max_length=11, min_length=11, label=_("Mobile number"))

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

        r = re.compile(r'(201|01|05|07)\d{8}')
        if not r.match(msisdn):
            raise forms.ValidationError(_("Mobile number is not valid"))
        if Agent.objects.filter(msisdn=msisdn).exists():
            raise forms.ValidationError(
                _("Please Provide new agent because this agent already exist.")
            )
        return msisdn


class ExistingAgentForm(forms.ModelForm):
    """
    Agent form for adding agents for newly created Admins using existing agents related to the current superadmin
    """

    msisdn = forms.ChoiceField(label=_("Mobile number"))

    class Meta:
        model = Agent
        fields = ('msisdn',)

    def __init__(self, *args, root, agents_choices, **kwargs):
        self.root = root
        super().__init__(*args, **kwargs)
        self.fields['msisdn'].choices = agents_choices

    def clean_msisdn(self):
        """
        :return: Validate the passed agent mobile number against r regex (EG, 010x, 011x, 012x)
        """
        msisdn = self.cleaned_data.get('msisdn', None)
        if not msisdn:
            return msisdn
        import re

        r = re.compile(r'(201|01)[0-2|5]\d{7}')
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
        widget=forms.PasswordInput(
            attrs={'size': 6, 'maxlength': 6, 'placeholder': _('Add new pin')}
        ),
    )

    def __init__(self, *args, root, **kwargs):
        self.root = root
        super().__init__(*args, **kwargs)
        if (
            self.root.is_vodafone_default_onboarding
            or self.root.is_banks_standard_model_onboaring
        ):
            self.agents = Agent.objects.filter(wallet_provider=root)
        else:
            self.agents = Agent.objects.filter(
                wallet_provider=root.super_admin)
        self.env = get_dot_env()

    def get_form(self):
        agent = self.agents.first()
        if (
            (
                self.root.is_vodafone_default_onboarding
                or self.root.is_banks_standard_model_onboaring
            )
            and agent
            and agent.pin
        ):
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

        if (
            self.root.is_vodafone_default_onboarding
            or self.root.is_banks_standard_model_onboaring
        ) and self.root.callwallets_moderator.first().set_pin:
            if self.root.client.agents_onboarding_choice in [
                Client.NEW_SUPERAGENT_AGENTS,
                Client.P2M,
            ]:
                msisdns = list(self.agents.values_list('msisdn', flat=True))
            elif (
                self.root.client.agents_onboarding_choice
                == Client.EXISTING_SUPERAGENT_NEW_AGENTS
            ):
                msisdns = list(
                    self.agents.filter(super=False).values_list(
                        'msisdn', flat=True)
                )
            else:
                msisdns = False

            if msisdns:
                transactions, error = self.call_wallet(raw_pin, msisdns)
                if error:
                    self.add_error('pin', error)
                    return False
                error = self.get_transactions_error(
                    transactions
                )  # handle transactions list
                if error:
                    self.add_error('pin', error)
                    return False

        self.agents.update(pin=True)
        self.root.set_pin(raw_pin)
        return True

    def call_wallet(self, pin, msisdns):
        superadmin = self.root.client.creator
        payload, payload_without_pin = superadmin.vmt.accumulate_set_pin_payload(
            msisdns, pin
        )
        try:
            WALLET_API_LOGGER.debug(
                f"[request] [set pin] [{self.root}] -- {payload_without_pin}"
            )
            response = requests.post(
                self.env.str(superadmin.vmt.vmt_environment), json=payload, verify=False
            )
        except Exception as e:
            WALLET_API_LOGGER.debug(
                f"[message] [set pin error] [{self.root}] -- {e.args}"
            )
            return None, MSG_PIN_SETTING_ERROR
        else:
            WALLET_API_LOGGER.debug(
                f"[response] [set pin] [{self.root}] -- {str(response.text)}"
            )

        if response.ok:
            response_dict = response.json()
            transactions = response_dict.get('TRANSACTIONS', None)
            if not transactions:
                error_message = response_dict.get('MESSAGE', None) or _(
                    "Failed to set pin"
                )
                return None, error_message
            return transactions, None
        return None, MSG_PIN_SETTING_ERROR

    def get_transactions_error(self, transactions):
        failed_trx = list(
            filter(lambda trx: trx['TXNSTATUS'] != "200", transactions))

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
                    error_message = (
                        "You cannot use an old PIN. For assistance call 7001"
                    )
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
        widget=forms.PasswordInput(
            attrs={'size': 6, 'maxlength': 6, 'placeholder': _('Enter pin')}
        ),
    )

    def clean_pin(self):
        """
        :return: Validate that pin is a valid number
        """
        pin = self.cleaned_data.get('pin')

        if pin and not pin.isnumeric():
            raise forms.ValidationError(_("Pin must be numeric"))
        return pin


class SingleStepTransactionForm(forms.Form):
    """
    single step transaction Form by Checker users
    """

    # 1. shared fields between all issuers
    amount = forms.IntegerField(
        label=_('Amount'),
        required=True,
        validators=[MinValueValidator(round(Decimal(1), 2))],
        widget=forms.TextInput(
            attrs={
                'placeholder': _('Enter Transaction Amount'),
                'class': 'form-control',
                'type': 'number',
                'id': 'trxAmount',
                'min': 1,
                'name': 'trxAmount',
            }
        ),
    )
    pin = forms.CharField(
        label=_('pin'),

        required=True,
        min_length=6,
        max_length=6,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'id': 'pin',
                'name': 'pin',
                'placeholder': _('Enter your pin'),
            }
        ),
    )
    issuer = forms.ChoiceField(
        label=_('Issuer'),
        required=True,
        choices=[
            ('bank_card', _('Bank Card')),
            ('vodafone', _('Vodafone')),
            ('etisalat', _('Etisalat')),
            ('orange', _('Orange')),
            ('bank_wallet', _('Bank Wallet')),
            ('aman', _('Aman')),
        ],
        widget=forms.Select(
            attrs={
                'class': 'form-control',
            }
        ),
    )
    # 2. bank card fields
    transaction_type = forms.CharField(
        label=_('transaction type'),
        required=False,
        widget=forms.Select(
            choices=(
                (tx_type, tx_type.replace('_', ' ').capitalize())
                for tx_type in VALID_BANK_TRANSACTION_TYPES_LIST
            ),
            attrs={'class': 'form-control',
                   'id': 'tx_type', 'name': 'trx_type'},
        ),
    )
    creditor_account_number = forms.CharField(
        label=_('acc. number'),
        required=False,
        max_length=34,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'id': 'accountNumber',
                'name': 'accountNumber',
                'placeholder': _('Enter account number'),
            }
        ),
    )
    creditor_name = forms.CharField(
        label=_('account name'),
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'id': 'full_name',
                'name': 'full_name',
                'placeholder': _('Enter full name'),
            }
        ),
    )
    creditor_bank = forms.ChoiceField(
        label=_('Bank Name'),
        required=False,
        choices=[(dic['code'], dic['name']) for dic in BANK_CODES],
        widget=forms.Select(
            attrs={'class': 'form-control',
                   'id': 'bank_name', 'name': 'bank_name'}
        ),
    )
    # 3. shared filed between vodafone, etisalat, aman, orange, bank wallet
    msisdn = forms.CharField(
        label=_('Msisdn'),
        required=False,
        max_length=11,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'id': 'msisdn',
                'name': 'msisdn',
                'placeholder': _('Enter Msisdn'),
            }
        ),
    )
    # 4. shared fields between orange, bank wallet
    full_name = forms.CharField(
        label=_('Full Name'),
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'id': 'full_name',
                'name': 'full_name',
                'placeholder': _('Enter Full Name'),
            }
        ),
    )
    # aman fields
    first_name = forms.CharField(
        label=_('First Name'),
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'id': 'first_name',
                'name': 'first_name',
                'placeholder': _('Enter First Name'),
            }
        ),
    )
    last_name = forms.CharField(
        label=_('Last Name'),
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'id': 'last_name',
                'name': 'last_name',
                'placeholder': _('Enter Last Name'),
            }
        ),
    )
    email = forms.CharField(
        label=_('Email'),
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'id': 'email',
                'type': 'email',
                'name': 'email',
                'placeholder': _('Enter Your Email'),
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

    def clean_pin(self):
        pin = self.cleaned_data.get('pin', None)

        if pin and not pin.isnumeric():
            raise forms.ValidationError(_('Pin must be numeric'))
        if (
            not pin
            or self.current_user.root.pin
            and not self.current_user.root.check_pin(pin)
        ):
            raise forms.ValidationError(_('Invalid pin'))

        return pin

    def clean_amount(self):
        amount = self.cleaned_data.get('amount', None)

        if not amount or not (
            str(amount).replace('.', '', 1).isdigit() and Decimal(amount) >= 1
        ):
            raise forms.ValidationError(_('Invalid amount'))
        if (
            self.current_user.is_checker
            and Decimal(self.current_user.level.max_amount_can_be_disbursed) < amount
        ):
            raise forms.ValidationError(
                _('Entered amount exceeds your maximum amount that can be disbursed')
            )
        if not self.current_user.from_accept or self.current_user.allowed_to_be_bulk:
            if not self.current_user.root.budget.within_threshold(
                Decimal(amount), "bank_card"
            ):
                raise forms.ValidationError(
                    _("Entered amount exceeds your current balance")
                )

        return round(Decimal(amount), 2)

    def clean_issuer(self):
        issuer = self.cleaned_data.get('issuer', None)
        if issuer and issuer not in [
            'bank_card',
            'Bank Card',
            'vodafone',
            'etisalat',
            'orange',
            'bank_wallet',
            'aman',
        ]:
            raise forms.ValidationError(
                _(
                    'issuer must be one of these \
                bank_card / Bank Card / vodafone / etisalat / orange / bank_wallet / aman'
                )
            )
        return issuer

    def validate_transaction_type(self):
        transaction_type = self.cleaned_data.get('transaction_type', None)
        if (
            not transaction_type
            or str(transaction_type).upper() not in VALID_BANK_TRANSACTION_TYPES_LIST
        ):
            return _('Invalid transaction purpose')
        return True

    def validate_creditor_account_number(self):
        creditor_account_number = self.cleaned_data.get(
            'creditor_account_number', None)
        account = (
            get_digits(str(creditor_account_number))
            if creditor_account_number
            else None
        )

        if not (account and 6 <= len(account) <= 20):
            return _('Invalid Account number')

        return True

    def validate_creditor_name(self):
        creditor_name = self.cleaned_data.get('creditor_name', None)

        if not creditor_name:
            return _('Invalid name')
        elif any(e in str(creditor_name) for e in '!%*+&,<=>'):
            return _("Symbols like !%*+&,<=> not allowed in full name")

        return True

    def validate_creditor_bank(self):
        creditor_bank = self.cleaned_data.get('creditor_bank', None)

        if not creditor_bank or str(creditor_bank).upper() not in VALID_BANK_CODES_LIST:
            return _('Invalid bank swift code')

        return True

    def phonenumber_form_validate(self, msisdn):
        """
        Function to validate an Egyptian phone number.
        The function raises appropriate validation exceptions for forms usage.
        """
        try:
            number = PhoneNumber.from_string(msisdn)
        except phonenumbers.NumberParseException as error:
            return error._msg
        if (
            not number.is_valid()
            or phonenumbers.phonenumberutil.region_code_for_country_code(
                phonenumbers.parse(number.as_international).country_code
            )
            != "EG"
        ):
            return _("Phone numbers entered are incorrect")
        return True

    def validate_msisdn(self):
        msisdn = f"+2{self.cleaned_data.get('msisdn', None)}"
        return self.phonenumber_form_validate(msisdn)

    def validate_full_name(self):
        full_name = self.cleaned_data.get('full_name', None)
        if not full_name:
            return _('This field is required')
        elif any(e in str(full_name) for e in '!%*+&,<=>'):
            return _("Symbols like !%*+&,<=> not allowed in full name")
        return True

    def validate_first_name(self):
        first_name = self.cleaned_data.get('first_name', None)
        if not first_name:
            return _('This field is required')
        elif any(e in str(first_name) for e in '!%*+&,<=>'):
            return _("Symbols like !%*+&,<=> not allowed in first name")
        return True

    def validate_last_name(self):
        last_name = self.cleaned_data.get('last_name', None)
        if not last_name:
            return _('This field is required')
        elif any(e in str(last_name) for e in '!%*+&,<=>'):
            return _("Symbols like !%*+&,<=> not allowed in last name")
        return True

    def validate_email(self):
        email = self.cleaned_data.get('email', None)
        if not email:
            return _('This field is required')
        return True

    def clean(self):
        data = self.cleaned_data
        issuer = data.get('issuer')
        validationErrors = {}
        if issuer == 'vodafone' or issuer == 'etisalat':
            valid_msisdn = self.validate_msisdn()
            if valid_msisdn != True:
                validationErrors['msisdn'] = [valid_msisdn]
        elif issuer == 'orange' or issuer == 'bank_wallet':
            valid_msisdn = self.validate_msisdn()
            if valid_msisdn != True:
                validationErrors['msisdn'] = [valid_msisdn]
            valid_full_name = self.validate_full_name()
            if valid_full_name != True:
                validationErrors['full_name'] = [valid_full_name]
        elif issuer == 'bank_card':
            if (
                not self.current_user.from_accept
                or self.current_user.allowed_to_be_bulk
            ):
                valid_trx_type = self.validate_transaction_type()
                if valid_trx_type != True:
                    validationErrors['transaction_type'] = [valid_trx_type]
            valid_cr_ac_num = self.validate_creditor_account_number()
            if valid_cr_ac_num != True:
                validationErrors['creditor_account_number'] = [valid_cr_ac_num]
            valid_cr_name = self.validate_creditor_name()
            if valid_cr_name != True:
                validationErrors['creditor_name'] = [valid_cr_name]
            valid_cr_bank = self.validate_creditor_bank()
            if valid_cr_bank != True:
                validationErrors['creditor_bank'] = [valid_cr_bank]
        elif issuer == 'aman':
            valid_msisdn = self.validate_msisdn()
            if valid_msisdn != True:
                validationErrors['msisdn'] = [valid_msisdn]
            valid_first_name = self.validate_first_name()
            if valid_first_name != True:
                validationErrors['first_name'] = [valid_first_name]
            valid_last_name = self.validate_last_name()
            if valid_last_name != True:
                validationErrors['last_name'] = [valid_last_name]
            valid_email = self.validate_email()
            if valid_email != True:
                validationErrors['email'] = [valid_email]

        if self.current_user.from_accept and not self.current_user.allowed_to_be_bulk:
            valid_trx_type = self.validate_transaction_type()
            if valid_trx_type != True:
                validationErrors['transaction_type'] = [valid_trx_type]

        if len(validationErrors.keys()) == 0:
            return data
        raise forms.ValidationError(validationErrors)

    def save(self, commit=True):
        single_step_bank_transaction = super().save(commit=False)

        single_step_bank_transaction.user_created = self.current_user
        category_purpose_dict = determine_trx_category_and_purpose(
            self.cleaned_data.get('transaction_type')
        )
        single_step_bank_transaction.category_code = category_purpose_dict.get(
            'category_code', 'CASH'
        )
        single_step_bank_transaction.purpose = category_purpose_dict.get(
            'purpose', 'CASH'
        )
        single_step_bank_transaction.is_single_step = True
        single_step_bank_transaction.corporate_code = get_from_env(
            'ACH_CORPORATE_CODE')
        single_step_bank_transaction.debtor_account = get_from_env(
            'ACH_DEBTOR_ACCOUNT')
        single_step_bank_transaction.currency = 'EGP'
        single_step_bank_transaction.debtor_address_1 = 'EG'
        single_step_bank_transaction.creditor_address_1 = 'EG'

        single_step_bank_transaction.save()
        return single_step_bank_transaction


AgentFormSet = modelformset_factory(
    model=Agent, form=AgentForm, min_num=1, validate_min=True, can_delete=True, extra=0)
ExistingAgentFormSet = modelformset_factory(model=Agent, form=ExistingAgentForm, min_num=1, validate_min=True,
                                            can_delete=True, extra=0)


class PaymentCreationForm(forms.Form):

    # 1. shared fields between all issuers
    amount = forms.IntegerField(
        label=_('Amount'),
        required=True,
        validators=[MinValueValidator(round(Decimal(1), 2))],
        widget=forms.TextInput(attrs={
            'placeholder': _('Enter Transaction Amount'), 'class': 'form-control',
            'type': 'number', 'id': 'trxAmount', 'min': 1, 'name': 'trxAmount'
        })
    )
    pin = forms.CharField(
        required=False,
        min_length=6,
        max_length=6,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 'id': 'pin',
            'name': 'pin', 'placeholder': 'Enter your pin'
        })
    )

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

    def clean_pin(self):
        pin = self.cleaned_data.get('pin', None)

        if pin and not pin.isnumeric():
            raise forms.ValidationError(_('Pin must be numeric'))
        if not pin or not self.current_user.root.check_pin(pin):
            raise forms.ValidationError(_('Invalid pin'))

        return pin

    def clean_amount(self):
        amount = self.cleaned_data.get('amount', None)

        if not amount or not (str(amount).replace('.', '', 1).isdigit() and Decimal(amount) >= 1):
            raise forms.ValidationError(_('Invalid amount'))
        if self.current_user.is_checker and Decimal(self.current_user.level.max_amount_can_be_disbursed) < amount:
            raise forms.ValidationError(
                _('Entered amount exceeds your maximum amount that can be disbursed'))
        if not self.current_user.root.budget.within_threshold(Decimal(amount), "bank_card"):
            raise forms.ValidationError(
                _("Entered amount exceeds your current balance"))

        return round(Decimal(amount), 2)


class DisbursePaymentLinkForm(forms.Form):
    issuer = forms.ChoiceField(
        label=_('Issuer'),
        required=True,
        choices=[
            ('bank_card', 'Bank Card'),
            ('vodafone', 'Vodafone'),
            ('etisalat', 'Etisalat'),
            ('orange', 'Orange'),
            ('bank_wallet', 'Bank Wallet'),
            ('aman', 'Aman')
        ],
        widget=forms.Select(attrs={
            'class': 'form-control',
        })
    )

    # 1. bank card fields
    transaction_type = forms.CharField(
        required=False,
        widget=forms.Select(
            choices=(
                (tx_type, tx_type.replace('_', ' ').capitalize()) for tx_type in VALID_BANK_TRANSACTION_TYPES_LIST
            ),
            attrs={'class': 'form-control',
                   'id': 'tx_type', 'name': 'trx_type'}
        )
    )
    creditor_account_number = forms.CharField(
        label=_('acc. number'),
        required=False,
        max_length=34,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'id': 'accountNumber',
            'name': 'accountNumber', 'placeholder': 'Enter account number'
        })
    )
    creditor_name = forms.CharField(
        label=_('account name'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'id': 'full_name',
            'name': 'full_name', 'placeholder': 'Enter full name'
        })
    )
    creditor_bank = forms.ChoiceField(
        label=_('Bank Name'),
        required=False,
        choices=[(dic['code'], dic['name']) for dic in BANK_CODES],
        widget=forms.Select(attrs={
            'class': 'form-control', 'id': 'bank_name', 'name': 'bank_name'
        })
    )
    # 2. shared filed between vodafone, etisalat, aman, orange, bank wallet
    msisdn = forms.CharField(
        label=_('Msisdn'),
        required=False,
        max_length=11,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'id': 'msisdn',
            'name': 'msisdn', 'placeholder': 'Enter Msisdn'
        })
    )
    # 3. shared fields between orange, bank wallet
    full_name = forms.CharField(
        label=_('Full Name'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'id': 'full_name',
            'name': 'full_name', 'placeholder': 'Enter Full Name'
        })
    )
    # aman fields
    first_name = forms.CharField(
        label=_('First Name'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'id': 'first_name',
            'name': 'first_name', 'placeholder': 'Enter First Name'
        })
    )
    last_name = forms.CharField(
        label=_('Last Name'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'id': 'last_name',
            'name': 'last_name', 'placeholder': 'Enter Last Name'
        })
    )
    email = forms.CharField(
        label=_('Email'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'id': 'email', 'type': 'email',
            'name': 'email', 'placeholder': 'Enter Your Email'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate_transaction_type(self):
        transaction_type = self.cleaned_data.get('transaction_type', None)
        if not transaction_type or str(transaction_type).upper() not in VALID_BANK_TRANSACTION_TYPES_LIST:
            return _('Invalid transaction purpose')
        return True

    def validate_creditor_account_number(self):
        creditor_account_number = self.cleaned_data.get(
            'creditor_account_number', None)
        account = get_digits(str(creditor_account_number)
                             ) if creditor_account_number else None

        if not (account and 6 <= len(account) <= 20):
            return _('Invalid Account number')

        return True

    def validate_creditor_name(self):
        creditor_name = self.cleaned_data.get('creditor_name', None)

        if not creditor_name:
            return _('Invalid name')
        elif any(e in str(creditor_name) for e in '!%*+&,<=>'):
            return _("Symbols like !%*+&,<=> not allowed in full name")

        return True

    def validate_creditor_bank(self):
        creditor_bank = self.cleaned_data.get('creditor_bank', None)

        if not creditor_bank or str(creditor_bank).upper() not in VALID_BANK_CODES_LIST:
            return _('Invalid bank swift code')

        return True

    def phonenumber_form_validate(self, msisdn):
        """
        Function to validate an Egyptian phone number.
        The function raises appropriate validation exceptions for forms usage.
        """
        try:
            number = PhoneNumber.from_string(msisdn)
        except phonenumbers.NumberParseException as error:
            return error._msg
        if (
                not number.is_valid()
                or phonenumbers.phonenumberutil.region_code_for_country_code(
                phonenumbers.parse(number.as_international).country_code
                )
                != "EG"
        ):
            return _("Phone numbers entered are incorrect")
        return True

    def validate_msisdn(self):
        msisdn = f"+2{self.cleaned_data.get('msisdn', None)}"
        return self.phonenumber_form_validate(msisdn)

    def validate_full_name(self):
        full_name = self.cleaned_data.get('full_name', None)
        if not full_name:
            return _('This field is required')
        elif any(e in str(full_name) for e in '!%*+&,<=>'):
            return _("Symbols like !%*+&,<=> not allowed in full name")
        return True

    def validate_first_name(self):
        first_name = self.cleaned_data.get('first_name', None)
        if not first_name:
            return _('This field is required')
        elif any(e in str(first_name) for e in '!%*+&,<=>'):
            return _("Symbols like !%*+&,<=> not allowed in first name")
        return True

    def validate_last_name(self):
        last_name = self.cleaned_data.get('last_name', None)
        if not last_name:
            return _('This field is required')
        elif any(e in str(last_name) for e in '!%*+&,<=>'):
            return _("Symbols like !%*+&,<=> not allowed in last name")
        return True

    def validate_email(self):
        email = self.cleaned_data.get('email', None)
        if not email:
            return _('This field is required')
        return True

    def clean_issuer(self):
        issuer = self.cleaned_data.get('issuer', None)
        if issuer and issuer \
                not in ['bank_card', 'Bank Card', 'vodafone', 'etisalat', 'orange', 'bank_wallet', 'aman']:
            raise forms.ValidationError(_('issuer must be one of these \
                bank_card / Bank Card / vodafone / etisalat / orange / bank_wallet / aman'))
        return issuer
