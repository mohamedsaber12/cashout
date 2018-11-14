from django.conf import settings
from django.db import models

from data.models import Doc
from users.models import CheckerUser


class DocReview(models.Model):
    is_ok = models.BooleanField(default=False)
    doc = models.ForeignKey(Doc, on_delete=models.CASCADE)
    user_created = models.ForeignKey(CheckerUser, on_delete=models.CASCADE)
    comment = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateField(auto_now_add=True)
