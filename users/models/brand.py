from django.db import models
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill


class Brand(models.Model):
    """
    Entity Brand
    """
    color = models.CharField(max_length=20, null=True, blank=True)
    logo = ProcessedImageField(upload_to='entities-logo',
                                      processors=[ResizeToFill(100, 100)],
                                      format='JPEG',
                               options={'quality': 60}, null=True, default='pm_name.png')

