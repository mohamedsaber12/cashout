import logging

from django import forms
from django.forms import modelformset_factory
from django.utils.translation import gettext as _

from payouts.utils import get_dot_env
from users.tasks import set_pin_error_mail

from .models import Agent, VMTData


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
        self.agents = Agent.objects.filter(wallet_provider=root)
        self.env = get_dot_env()

    def get_form(self):
        agent = self.agents.first()
        if agent and agent.pin:
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
        msisdns = list(self.agents.values_list('msisdn', flat=True))
        if self.env.str('CALL_WALLETS', 'TRUE') == 'TRUE':
            transactions, error = self.call_wallet(raw_pin, msisdns)
            if error:
                self.add_error('pin', error)
                return False
            error = self.get_transactions_error(transactions)       # handle transactions list
            if error:
                self.add_error('pin', error)
                return False

        self.agents.update(pin=True)
        return True

    # ToDo Move call wallets to dedicated VMTData class methods
    def call_wallet(self, pin, msisdns):
        import requests
        superadmin = self.root.client.creator
        vmt = VMTData.objects.get(vmt=superadmin)
        data = vmt.return_vmt_data(VMTData.SET_PIN)
        data["USERS"] = msisdns
        data["PIN"] = pin
        try:
            response = requests.post(self.env.str(vmt.vmt_environment), json=data, verify=False)
        except Exception as e:
            WALLET_API_LOGGER.debug(f"""[SET PIN ERROR]
            Users-> root(admin):{self.root.username}, vmt(superadmin):{superadmin.username}
            Error-> {e}""")
            return None, MSG_PIN_SETTING_ERROR

        WALLET_API_LOGGER.debug(f"""[SET PIN]
        Users-> root(admin):{self.root.username}, vmt(superadmin):{superadmin.username}
        Response-> {str(response.status_code)} -- {str(response.text)}""")
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


AgentFormSet = modelformset_factory(model=Agent, form=AgentForm, can_delete=True, min_num=1, validate_min=True)
