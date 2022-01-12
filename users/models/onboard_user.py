# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import gettext_lazy as _

from .base_user import User, UserManager


class OnboardUserManager(UserManager):
    """
    Manager for Onboard user
    """

    def get_queryset(self):
        return super().get_queryset().filter(user_type=9)

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('user_type', 9)
        return self._create_user(username, email, password, **extra_fields)


class OnboardUser(User):
    """
    OnboardUser/Customer care user who can onboard new entities/roots .
    """

    objects = OnboardUserManager()

    class Meta:
        proxy = True


class OnboardUserSetup(models.Model):
    """
    Onboard User Setup model to link and save the state of the onboard user setups by super admin
    """

    onboard_user = models.OneToOneField(
            OnboardUser,
            on_delete=models.CASCADE,
            related_name='my_onboard_setups',
            verbose_name=_('Onboard User')
    )
    user_created = models.ForeignKey(
            'users.SuperAdminUser',
            on_delete=models.CASCADE,
            related_name='onboard_user_setups',
            verbose_name=_('Super Admin User')
    )

    class Meta:
        ordering = ['-id']

    def __str__(self):
        "String representation of each onboard setup object"
        return f'{self.user_created} setup for {self.onboard_user}'
