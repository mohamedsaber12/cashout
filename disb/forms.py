from django import forms

from disb.models import Agent


class AgentForm(forms.ModelForm):
    pin = forms.CharField(widget=forms.TextInput(attrs={'size': 6, 'maxlength': 6}))

    class Meta:
        model = Agent
        exclude = ('wallet_provider',)
