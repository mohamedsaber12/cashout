from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.crypto import get_random_string

from users.models import RootUser, MakerUser, CheckerUser, Setup


ALLOWED_CHARACTERS = '!#$%&*+-0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ^_abcdefghijklmnopqrstuvwxyz'
MESSAGE = 'Dear {0}\n' \
          'This account is created on the panel with random password {1}\n' \
          'Please reset this password as soon as possible, \n' \
          'Thanks, BR'



@receiver(post_save, sender=RootUser)
def create_setup(sender, instance, created, **kwargs):
    if created:
        Setup.objects.create(user=instance)


def notify_user(sender, instance, created, **kwargs):
    if created:
        random_pass = get_random_string(allowed_chars=ALLOWED_CHARACTERS, length=12)
        instance.set_password(random_pass)
        instance.save()
        send_mail(
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[instance.email],
            subject='[Payroll] Password Notification',
            message=MESSAGE.format(instance.first_name, random_pass)
        )


@receiver(post_save, sender=MakerUser)
def send_random_pass_to_maker(sender, instance, created, **kwargs):
    notify_user(sender, instance, created, **kwargs)


@receiver(post_save, sender=CheckerUser)
def send_random_pass_to_checker(sender, instance, created, **kwargs):
    notify_user(sender, instance, created, **kwargs)


