from django.db.models.signals import post_save
from django.dispatch import receiver
from users.models import User, Setup


@receiver(post_save, sender=User)
def create_setup(sender,instance, **kwargs):
    if instance.is_parent:
        Setup.objects.create(user=instance)
