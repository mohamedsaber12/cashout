from uuid import uuid4

from django.db import models


class AccessToken(models.Model):
    token = models.CharField(max_length=255)
    used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = uuid4()
        return super(AccessToken, self).save(*args, **kwargs)
