# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import gettext_lazy as _

from .base_user import User, UserManager


class SupportManager(UserManager):
    """
    Manager for support user
    """

    def get_queryset(self):
        return super().get_queryset().filter(user_type=8)

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('user_type', 8)
        return self._create_user(username, email, password, **extra_fields)


class SupportUser(User):
    """
    Support/Customer care user who can view on-boarded entities/roots or on-board entities.
    """

    objects = SupportManager()

    class Meta:
        proxy = True


class SupportSetup(models.Model):
    """
    Support Setup model to link and save the state of the support user setups by super admin
    """

    support_user = models.OneToOneField(
            SupportUser,
            on_delete=models.CASCADE,
            related_name='my_setups',
            verbose_name=_('Support User')
    )
    user_created = models.ForeignKey(
            'users.SuperAdminUser',
            on_delete=models.CASCADE,
            related_name='support_setups',
            verbose_name=_('Super Admin User')
    )
    can_onboard_entities = models.BooleanField(default=False, verbose_name=_('Can On-board Entities?'))

    class Meta:
        ordering = ['-id']

    def __str__(self):
        "String representation of each support setup object"
        return f'{self.user_created} setup for {self.support_user}'
