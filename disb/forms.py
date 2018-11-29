from django import forms
from django.forms import modelformset_factory

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
    pin = forms.CharField(widget=forms.PasswordInput(attrs={'size': 6, 'maxlength': 6, 'placeholder':'Pin'}))


AgentFormSet = modelformset_factory(
    model=Agent, form=AgentForm, can_delete=True)
