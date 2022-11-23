from django.db import models
from django import forms
import os, uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import  AbstractTimeStamp

from data.utils import upload_filename


class Merchant(AbstractTimeStamp):

    id = models.CharField(
        primary_key=True, editable=False, unique=True, db_index=True,
        max_length=36, default=uuid.uuid4
    )
    merchant = models.ForeignKey(
            "users.Client",
            on_delete=models.CASCADE,
            related_name='legaldocument',
            verbose_name=_("merchant"),
            null=False
    )

    class Meta:
        verbose_name_plural = 'Merchant'

    
    def __str__(self):
        return str(f"{self.merchant.client.username}")

class FileLegalDocs(models.Model):
    
    verified = models.BooleanField(null=True, default=False, help_text=_("Document is verified or no"))
    verified_by=models.ForeignKey(
            "users.User",
            on_delete=models.CASCADE,
            related_name='my_verified_docs',
            verbose_name=_("verified_by"),
            null=True,
            blank=True,
            
    )
    filename=models.CharField(max_length=255, null=True, blank=True, help_text=_("File name"))
    file = models.FileField(upload_to=upload_filename,  blank=False,null=True,default="")    
    merchant = models.ForeignKey("merchants.Merchant", on_delete=models.CASCADE, related_name='my_legal_docs',null=True)
    comment= models.CharField(max_length=255, null=True, blank=True, help_text=_("Empty if the verified is ok"))
    timestamp = models.DateField(auto_now_add=True)


    class Meta:
        verbose_name_plural = 'Legal File'

    def __str__(self):
       
        return str(self.filename)

class FileLegalDocsForm(forms.ModelForm):
    def clean(self):
        filename = self.cleaned_data['filename']
        if not filename in ["CR", "TXID", "CONTRACT", "IDS", "PASSPORT"] :

            raise forms.ValidationError({'filename': "This field must be one if this (CR, TXID, CONTRACT, IDS, PASSPORT)"})