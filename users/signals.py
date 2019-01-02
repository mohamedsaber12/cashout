from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext as _

from users.models import CheckerUser, MakerUser, RootUser, Setup, Brand, SuperAdminUser,Client

ALLOWED_CHARACTERS = '!#$%&*+-0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ^_abcdefghijklmnopqrstuvwxyz'
MESSAGE = 'Dear {0}\n' \
          'Your account is created on the panel with email: {2} and username: {3} \n' \
          'Please follow <a href="{1}">this link</a> to reset password as soon as possible, \n' \
          'Thanks, BR'


@receiver(post_save, sender=RootUser)
def create_setup(sender, instance, created, **kwargs):
    notify_user(sender, instance, created, **kwargs)
    if created:
        Setup.objects.create(user=instance)


@receiver(post_save, sender=MakerUser)
def send_random_pass_to_maker(sender, instance, created, **kwargs):
    notify_user(sender, instance, created, **kwargs)


@receiver(post_save, sender=CheckerUser)
def send_random_pass_to_checker(sender, instance, created, **kwargs):
    notify_user(sender, instance, created, **kwargs)


@receiver(pre_save, sender=CheckerUser)
def checker_pre_save(sender, instance, *args, **kwargs):
    instance.username = generate_username(instance, sender)
    set_brand(instance)

@receiver(pre_save, sender=MakerUser)
def maker_pre_save(sender, instance, *args, **kwargs):
    instance.username = generate_username(instance, sender)
    set_brand(instance)

@receiver(pre_save, sender=SuperAdminUser)
def super_admin_pre_save(sender, instance, *args, **kwargs):
    if not instance.brand:
        instance.brand = Brand.objects.create()


@receiver(post_save, sender=Client)
def client_post_save(sender, instance,created, **kwargs):
    if created:
        set_client_brand(instance)


def set_brand(instance):
    if not instance.brand:
        instance.brand = instance.super_admin.brand


def set_client_brand(instance):
    instance.client.brand = instance.creator.brand


def generate_username(user, user_model):
    """
    Generate username for maker and checker in this format: 
    {first_name}-{last_name}-{hierarchy}-{user_type}'
    if new user has same first and last name then format is
    {first_name}-{last_name}-{hierarchy}-{user_type}-
    {no of users with same first and last name + 1}'
    """
    # user already exist
    if user.id:
        existing_user = user_model.objects.get(id=user.id)
        # first and last name are not changed
        if existing_user.first_name == user.first_name and existing_user.last_name == user.last_name:
            return user.username

    # new user or existing user updating first name or/and last name
    username = f'{user.first_name}-{user.last_name}-{user.hierarchy}-{user.user_type}'
    user_qs = user_model.objects.filter(username__contains=username)
    if not user_qs.exists():
        return username
    username = f'{username}-{ user_qs.count() + 1 }'
    return username


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
            subject=_('[Payroll] Password Notification'),
            message=MESSAGE.format(instance.first_name,
                                   url, instance.email, instance.username)
        )
