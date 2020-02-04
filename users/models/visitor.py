from django.conf import settings
from django.db import models


class Visitor(models.Model):
    session_key = models.CharField(null=False, max_length=40)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=False, related_name='visitor', on_delete=models.CASCADE)
