from django.db import models

from imagekit.models import ProcessedImageField


class Brand(models.Model):
    """
    Entity Brand
    """
    color = models.CharField(max_length=20, null=True, blank=True)
    logo = ProcessedImageField(upload_to='entities_logo',
                               format='JPEG',
                               options={'quality': 60}, null=True, default='entities_logo/pm_name.png')

    mail_subject = models.CharField(max_length=200, null=True, blank=True, default='Paymob Send')
