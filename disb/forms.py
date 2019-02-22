from django import forms
from django.forms import modelformset_factory
from django.utils.translation import gettext as _

from disb.models import Agent, VMTData


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
    class Meta:
        model = Agent
        fields = ('msisdn',)

    def __init__(self, *args, root, **kwargs):
        self.root = root
        super().__init__(*args, **kwargs)


class PinForm(forms.Form):

    pin = forms.CharField(required=True,max_length=6,min_length=6, widget=forms.PasswordInput(
            attrs={'size': 6, 'maxlength': 6, 'placeholder': _('Pin')}))

    def __init__(self, *args, root, **kwargs):
        self.root = root
        super().__init__(*args, **kwargs)
        self.agents = Agent.objects.filter(wallet_provider=root)
        agent = self.agents.first()
        for field_name, field in self.fields.items():
            if field_name == 'pin':
                if agent and not agent.pin:
                    field.label = _("Add new pin")
                else:
                    field.label = _("Change pin")
                    field.required = False
                break

    def save_agents(self):
        raw_pin = self.cleaned_data.get('pin')
        if not raw_pin:
            return
        agent = self.agents.first()
        agent.set_pin(raw_pin,commit=False)
        hashed_pin = agent.pin
        self.agents.update(pin=hashed_pin)

AgentFormSet = modelformset_factory(
    model=Agent, form=AgentForm, can_delete=True)
