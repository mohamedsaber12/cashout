from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from users.models import CheckerUser, MakerUser, RootUser, Setup

ALLOWED_CHARACTERS = '!#$%&*+-0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ^_abcdefghijklmnopqrstuvwxyz'
MESSAGE = 'Dear {0}\n' \
          'Your account is created on the panel with email: {2} \n' \
          'Please follow <a href="{1}">this link</a> to reset password as soon as possible, \n' \
          'Thanks, BR'


@receiver(post_save, sender=RootUser)
def create_setup(sender, instance, created, **kwargs):
    if created:
        Setup.objects.create(user=instance)


def notify_user(sender, instance, created, **kwargs):
    if created:
        random_pass = get_random_string(
            allowed_chars=ALLOWED_CHARACTERS, length=12)
        instance.set_password(random_pass)
        instance.save()

        # one time token
        token = default_token_generator.make_token(instance)
        uid = urlsafe_base64_encode(force_bytes(instance.pk)).decode("utf-8")
        url = settings.BASE_URL + reverse('users:password_reset_confirm', kwargs={
            'uidb64': uid, 'token': token})

        send_mail(
            from_email=settings.SERVER_EMAIL,
            recipient_list=[instance.email],
            subject='[Payroll] Password Notification',
            message=MESSAGE.format(instance.first_name, url, instance.email)
        )


@receiver(post_save, sender=MakerUser)
def send_random_pass_to_maker(sender, instance, created, **kwargs):
    notify_user(sender, instance, created, **kwargs)


@receiver(post_save, sender=CheckerUser)
def send_random_pass_to_checker(sender, instance, created, **kwargs):
    notify_user(sender, instance, created, **kwargs)
