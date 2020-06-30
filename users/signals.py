# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext as _

from utilities.models import CallWalletsModerator

from .models import Brand, CheckerUser, Client, MakerUser, RootUser, Setup, SuperAdminUser, SupportSetup, UploaderUser


ALLOWED_CHARACTERS = '!#$%&*+-0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ^_abcdefghijklmnopqrstuvwxyz'
MESSAGE = _("""Dear <strong>{0}</strong><br><br>
Your account is created on the panel with email: <strong>{2}</strong> and username: <strong>{3}</strong> <br>
Please follow <a href="{1}" ><strong>this link</strong></a> to reset password as soon as possible, <br><br>
Thanks, BR""")


@receiver(post_save, sender=RootUser)
def create_setup(sender, instance, created, **kwargs):
    if created:
        Setup.objects.create(user=instance)
        CallWalletsModerator.objects.create(user_created=instance)
        instance.user_permissions.add(
                Permission.objects.get(content_type__app_label='users', codename='has_disbursement')
        )


@receiver(post_save, sender=UploaderUser)
def send_random_pass_to_uploader(sender, instance, created, **kwargs):
    notify_user(instance, created)


@receiver(post_save, sender=MakerUser)
def send_random_pass_to_maker(sender, instance, created, **kwargs):
    notify_user(instance, created)


@receiver(post_save, sender=CheckerUser)
def send_random_pass_to_checker(sender, instance, created, **kwargs):
    notify_user(instance, created)


@receiver(pre_save, sender=CheckerUser)
def checker_pre_save(sender, instance, *args, **kwargs):
    generate_username(instance, sender)
    set_brand(instance)


@receiver(pre_save, sender=MakerUser)
def maker_pre_save(sender, instance, *args, **kwargs):
    generate_username(instance, sender)
    set_brand(instance)


@receiver(pre_save, sender=UploaderUser)
def uploader_pre_save(sender, instance, *args, **kwargs):
    generate_username(instance, sender)
    set_brand(instance)


@receiver(pre_save, sender=SuperAdminUser)
def super_admin_pre_save(sender, instance, *args, **kwargs):
    if not instance.brand:
        instance.brand = Brand.objects.create()


@receiver(post_save, sender=Client)
def client_post_save(sender, instance, created, **kwargs):
    if created:
        root_user = instance.client
        root_user.brand = instance.creator.brand
        root_user.save()
        notify_user(root_user, created)


@receiver(post_save, sender=SupportSetup)
def support_post_save(sender, instance, created, **kwargs):
    """Post save signal to send password setup email after creating any support user"""
    if created:
        support_user = instance.support_user
        support_user.brand = instance.user_created.brand
        support_user.save()
        notify_user(support_user, created)


def set_brand(instance):
    if not instance.brand:
        instance.brand = instance.super_admin.brand


def generate_username(user, user_model):
    """
    Generate username for make, checker and uploader in this format:
    {first_name}-{last_name}-{hierarchy}-{user_type}'
    if new user has same first and last name then format is
    {first_name}-{last_name}-{hierarchy}-{user_type}-
    {no of users with same first and last name + 1}'
    """
    # user already exist
    if user.id:
        return
    # new user
    username = f'{user.first_name}-{user.last_name}-{user.hierarchy}-{user.user_type}'
    user_qs = user_model.objects.filter(username__contains=username)
    if not user_qs.exists():
        user.username = username
        return
    username = f'{username}-{ user_qs.count() + 1 }'
    user.username = username


def notify_user(instance, created):
    if created:
        random_pass = get_random_string(allowed_chars=ALLOWED_CHARACTERS, length=12)
        instance.set_password(random_pass)
        instance.save()

        # one time token
        token = default_token_generator.make_token(instance)
        uid = urlsafe_base64_encode(force_bytes(instance.pk))
        url = settings.BASE_URL + reverse('users:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})

        from_email = settings.SERVER_EMAIL
        subject = f'[{instance.brand.mail_subject}]'
        subject = subject + _(' Password Notification')
        message = MESSAGE.format(instance.username, url, instance.email, instance.username)
        recipient_list = [instance.email]
        mail_to_be_sent = EmailMultiAlternatives(subject, message, from_email, recipient_list)
        mail_to_be_sent.attach_alternative(message, "text/html")
        mail_to_be_sent.send()
