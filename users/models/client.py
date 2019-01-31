from django.db import models
from users.models import User

class ClientManager(models.Manager):
    def toggle(self, *args, **kwargs):
        try:
            user = self.get(*args, **kwargs)
            user.toggle_activation()
            return True
        except:
            return False


class Client(models.Model):
    creator = models.ForeignKey('users.SuperAdminUser', on_delete=models.SET_NULL, related_name='clients', null=True)
    client = models.OneToOneField('users.RootUser', on_delete=models.CASCADE, null=True, related_name='client')
    is_active = models.BooleanField(default=True)
    objects = ClientManager()

    def __str__(self):
        return ''
        return f'The client {self.client.username} by {self.creator}'

    def toggle_activation(self):
        self.is_active = not self.is_active
        self.save()

    def delete_client(self):
        User.objects.filter(hierarchy=self.client.hierarchy).delete()
        self.delete()
