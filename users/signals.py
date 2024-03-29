import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext as _
import requests

from instant_cashin.utils import get_from_env
from .models import (
    Brand, CheckerUser, Client, MakerUser, SuperAdminUser, SupportSetup, UploaderUser,
    OnboardUserSetup, SupervisorSetup
)
from users.sso import SSOIntegration
from users import models


SEND_EMAIL_LOGGER = logging.getLogger("send_emails")
WALLET_API_LOGGER = logging.getLogger("wallet_api")
ALLOWED_UPPER_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
ALLOWED_LOWER_CHARS = 'abcdefghijklmnopqrstuvwxyz'
ALLOWED_SYMBOLS = '!#$%&*+-:;<=>?@^_'
ALLOWED_NUMBERS = '0123456789'
MESSAGE = _("""Dear <strong>{0}</strong><br><br>
Your account is created on the panel with email: <strong>{2}</strong> and username: <strong>{3}</strong> <br>
Please follow <a href="{1}" ><strong>this link</strong></a> to reset password as soon as possible, <br><br>
Thanks, BR""")
VODAFONE_ACTIVATION_MESSAGE = _(
        "Your payroll account has been registered successfully. "
        "Please open your email to activate your payroll account, or you can activate your account by using the "
        "following credentials: username: {0} and the link to set your password: {1}. To learn more about "
        "the usage method, click on {2} or view {3}"
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

@receiver(post_save, sender=OnboardUserSetup)
def onboard_user_post_save(sender, instance, created, **kwargs):
    """Post save signal to send password setup email after creating any onboard user"""
    if created:
        onboard_user = instance.onboard_user
        onboard_user.brand = instance.user_created.brand
        onboard_user.save()
        # Register User Over IDMS
        sso =  SSOIntegration()
        sso.register_user_on_idms(onboard_user)
        notify_user(onboard_user, created)


@receiver(post_save, sender=models.User)
@receiver(post_save, sender=models.InstantAPIViewerUser)
@receiver(post_save, sender=models.RootUser)
@receiver(post_save, sender=models.CheckerUser)
@receiver(post_save, sender=models.MakerUser)
@receiver(post_save, sender=models.UploaderUser)
@receiver(post_save, sender=models.UpmakerUser)
@receiver(post_save, sender=models.InstantAPICheckerUser)
@receiver(post_save, sender=models.SuperAdminUser)
@receiver(post_save, sender=models.OnboardUser)
@receiver(post_save, sender=models.SupportUser)
@receiver(post_save, sender=models.SupervisorUser)
def all_users_signal(sender, instance, created, **kwargs):
    sso =  SSOIntegration()
    if created:
        # Register User Over IDMS
        sso.register_user_on_idms(instance)
    else:
        # Edit User on IDMS
        sso.edit_user_on_idms(instance)



@receiver(post_save, sender=SupervisorSetup)
def supervisor_post_save(sender, instance, created, **kwargs):
    """Post save signal to send password setup email after creating any supervisor user"""
    if created:
        supervisor_user = instance.supervisor_user
        supervisor_user.brand = instance.user_created.brand
        supervisor_user.save()
        notify_user(supervisor_user, created)


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


def send_activation_message(root_user, set_password_url, forget_password_msg=False):
    send_staging_url = "https://stagingvodafonepayouts.paymob.com"
    send_production_url = "https://vodafonepayouts.paymob.com"
    superadmin = root_user.client.creator

    if len(root_user.mobile_no) > 10 and len(root_user.client.smsc_sender_name) > 3:
        if superadmin.vmt.vmt_environment == "STAGING":
            msg_env_url = "MESSAGE_STAGING_URL"
            send_env_url = send_staging_url
        else:
            msg_env_url = "MESSAGE_PRODUCTION_URL"
            send_env_url = send_production_url

        payload = {
            "TYPE": "SMSREQ",
            "MSISDN": f"{root_user.mobile_no}",
            "TEXT": VODAFONE_ACTIVATION_MESSAGE.format(
                    root_user.username, set_password_url, send_env_url, "Link to an infographic video"
            ),
            "SMSSENDER": f"{root_user.client.smsc_sender_name}"
        }
        if forget_password_msg:
            payload["TEXT"] = f"Click this link to reset your password {set_password_url}"
        # delete SMSSENDER from payload if it's empty
        if not root_user.client.smsc_sender_name:
            del(payload["SMSSENDER"])

        # delete SMSSENDER from payload if root is_vodafone_default_onboarding
        if root_user.is_vodafone_default_onboarding:
            del(payload["SMSSENDER"])

        try:
            WALLET_API_LOGGER.debug(f"[request] [activation message] [{root_user}] -- {payload}, url: {msg_env_url}")
            response = requests.post(get_from_env(msg_env_url), json=payload, verify=False)
        except Exception as e:
            WALLET_API_LOGGER.debug(f"[message] [activation message error] [{root_user}] -- {e.args}")
        else:
            WALLET_API_LOGGER.debug(f"[response] [activation message] [{root_user}] -- {str(response.text)}")


def notify_user(instance, created):
    if created:
        random_pass = get_random_string(allowed_chars=ALLOWED_UPPER_CHARS, length=5)
        random_pass += get_random_string(allowed_chars=ALLOWED_LOWER_CHARS, length=5)
        random_pass += get_random_string(allowed_chars=ALLOWED_NUMBERS, length=4)
        random_pass += get_random_string(allowed_chars=ALLOWED_SYMBOLS, length=4)
        instance.set_password(random_pass)
        instance.save()

        # one time token
        token = default_token_generator.make_token(instance)
        uid = urlsafe_base64_encode(force_bytes(instance.pk))
        url = settings.BASE_URL + reverse('users:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})

        if instance.is_root and (instance.is_vodafone_default_onboarding or instance.is_banks_standard_model_onboaring):
            send_activation_message(instance, url)

        from_email = settings.SERVER_EMAIL
        if instance.brand:
            subject = f'[{instance.brand.mail_subject}]'
        else:
            subject = 'Paymob Send'
        subject = subject + _(' Password Notification')
        message = MESSAGE.format(instance.username, url, instance.email, instance.username)
        recipient_list = [instance.email]
        mail_to_be_sent = EmailMultiAlternatives(subject, message, from_email, recipient_list)
        mail_to_be_sent.attach_alternative(message, "text/html")
        mail_to_be_sent.send()
        SEND_EMAIL_LOGGER.debug(
            f"[{subject}] [{recipient_list[0]}] -- {message}"
        )