from __future__ import unicode_literals

import os, uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import  AbstractTimeStamp

from ..utils import upload_filename


class LegalDoc(AbstractTimeStamp):
    """
    Model for representing uploaded document object
    """

    id = models.CharField(
        primary_key=True, editable=False, unique=True, db_index=True,
        max_length=36, default=uuid.uuid4
    )
    Client = models.ForeignKey(
            "users.Client",
            on_delete=models.CASCADE,
            related_name='legaldocument',
            verbose_name=_("Client/Root"),
            null=False
    )
    creator=models.ForeignKey(
            "users.SuperAdminUser",
            on_delete=models.CASCADE,
            related_name='legaldocument',
            verbose_name=_("SuperAdmin"),
            null=False)

    class Meta:
        verbose_name_plural = 'Legal Doc'

    
    def __str__(self):
        """
        :return: String representation for the DocReview model objects
        """
        return str(f"username: {self.id}")

    

class FileLegalDocs(models.Model):
    """
    Reviews made by checker users for uploaded documents
    """
    verified = models.BooleanField(null=True, default=False, help_text=_("Document is verified or no"))
    file = models.FileField(upload_to=upload_filename,  blank=False,null=True,default="")    
    doc = models.ForeignKey("data.LegalDoc", on_delete=models.CASCADE, related_name='reviews',null=True)
    comment= models.CharField(max_length=255, null=True, blank=True, help_text=_("Empty if the verified is ok"))
    timestamp = models.DateField(auto_now_add=True)


    class Meta:
        verbose_name_plural = 'Legal File'

    def __str__(self):
        """
        :return: String representation for the DocReview model objects
        """
        return str(self.file.name)
