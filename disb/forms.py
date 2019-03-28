import logging
from django import forms
from django.forms import modelformset_factory
from django.utils.translation import gettext as _
from disb.models import Agent, VMTData
from datetime import datetime
from users.tasks import set_pin_error_mail

WALLET_API_LOGGER = logging.getLogger("wallet_api")


class AgentAdminForm(forms.ModelForm):
    pin = forms.CharField(widget=forms.TextInput(attrs={'size': 6, 'maxlength': 6}))

    class Meta:
        model = Agent
        exclude = ('wallet_provider',)


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
    msisdn = forms.CharField(max_length=11,min_length=11,label=_("Mobile number"))
    class Meta:
        model = Agent
        fields = ('msisdn',)

    def __init__(self, *args, root, **kwargs):
        self.root = root
        super().__init__(*args, **kwargs)

    def clean_msisdn(self):
        msisdn = self.cleaned_data.get('msisdn',None)
        if not msisdn:
            return msisdn
        import re
        r = re.compile('(201|01)[0-2|5]\d{7}')
        if not r.match(msisdn):
            raise forms.ValidationError(_("Mobile number is not valid"))
        return msisdn    

class PinForm(forms.Form):

    pin = forms.CharField(required=True,max_length=6,min_length=6, widget=forms.PasswordInput(
        attrs={'size': 6, 'maxlength': 6, 'placeholder': _('Add new pin')}))

    def __init__(self, *args, root, **kwargs):
        self.root = root
        super().__init__(*args, **kwargs)
        self.agents = Agent.objects.filter(wallet_provider=root)

    def get_form(self):
        agent = self.agents.first()
        if agent and agent.pin:
            return None
        return self    

    def clean_pin(self):
        pin = self.cleaned_data.get('pin')
        if pin and not pin.isnumeric():
            raise forms.ValidationError(_("Pin must be numeric"))
        return pin

    def set_pin(self):
        raw_pin = self.cleaned_data.get('pin')
        if not raw_pin:
            return False
        msisdns = list(self.agents.values_list('msisdn', flat=True))
        transactions,error = self.call_wallet(raw_pin, msisdns)
        if error:
            self.add_error('pin',error)
            return False
        # handle transactions list 
        error = self.get_transactions_error(transactions)
        if error:
            self.add_error('pin', error)
            return False
        
        self.agents.update(pin=True)
        return True

    def call_wallet(self,pin,msisdns):
        import requests
        from disbursement.utils import get_dot_env
        env = get_dot_env()
        vmt = VMTData.objects.get(vmt=self.root.client.creator)
        data = vmt.return_vmt_data(VMTData.SET_PIN)
        data["USERS"] = msisdns
        data["PIN"] = pin
        response = requests.post(
            env.str(vmt.vmt_environment), json=data, verify=False)
        WALLET_API_LOGGER.debug(
            datetime.now().strftime('%d/%m/%Y %H:%M') + '----> SET PIN <-- \n' +
            str(response.status_code) + ' -- ' + str(response.text))
        if response.ok:
            response_dict = response.json()
            transactions = response_dict.get('transactions', None)
            if not transactions:
                error_message = response_dict.get(
                    'MESSAGE', None) or _("Failed to set pin")
                return None, error_message
            return transactions, None
        return None, _("Set pin process stopped during an internal error,\
                 can you try again or contact you support team")

    def get_transactions_error(self, transactions):
        failed_trx = list(filter(
            lambda trx: trx['TXNSTATUS'] != "200", transactions))
        if failed_trx:
            set_pin_error_mail.delay(self.root.id)
            return _("Failed to set pin")    
        return None

class BalanceInquiryPinForm(forms.Form):
    pin = forms.CharField(required=True, max_length=6, min_length=6, widget=forms.PasswordInput(
        attrs={'size': 6, 'maxlength': 6, 'placeholder': _('Enter pin')}))

    def clean_pin(self):
        pin = self.cleaned_data.get('pin')
        if pin and not pin.isnumeric():
            raise forms.ValidationError(_("Pin must be numeric"))
        return pin

        
AgentFormSet = modelformset_factory(
    model=Agent, form=AgentForm, can_delete=True, 
    min_num=1, validate_min=True)
