from django.db import models
from django import forms
import os, uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import  AbstractTimeStamp

from data.utils import upload_filename
from users.models import Client, RootUser
from users.models.base_user import  UserManager


class MerchantManager(UserManager):
    """
    Manager for Merchant user
    """
    def get_queryset(self):
        return super().get_queryset()

class Merchant(Client):

    objects = MerchantManager()

    class Meta:
        # verbose_name_plural = 'Merchant'
        proxy = True

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
    Merchant = models.ForeignKey(
           "merchants.Merchant" ,on_delete=models.CASCADE, null=True,related_name="my_legal_docs")
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