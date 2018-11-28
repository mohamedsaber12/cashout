from django.db import models


class Client(models.Model):
    creator = models.ForeignKey('users.SuperAdminUser', on_delete=models.DO_NOTHING, related_name='clients')
    client = models.OneToOneField('users.RootUser', on_delete=models.SET_NULL, null=True, related_name='client')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'The client {self.client.username} by {self.creator}'