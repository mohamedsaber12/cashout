# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import gettext_lazy as _

from .base_user import User, UserManager


class SupervisorManager(UserManager):
    """
    Manager for support user
    """

    def get_queryset(self):
        return super().get_queryset().filter(user_type=12)

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('user_type', 12)
        return self._create_user(username, email, password, **extra_fields)


class SupervisorUser(User):
    """
    Supervisor user who can add or delete Support/Customer care.
    """

    objects = SupervisorManager()

    class Meta:
        proxy = True


class SupervisorSetup(models.Model):
    """
    supervisor Setup model to link and save the state of the supervisor user setups by super admin
    """

    supervisor_user = models.OneToOneField(
            SupervisorUser,
            on_delete=models.CASCADE,
            related_name='my_setup',
            verbose_name=_('Supervisor User')
    )
    user_created = models.ForeignKey(
            'users.SuperAdminUser',
            on_delete=models.CASCADE,
            related_name='supervisor_setups',
            verbose_name=_('Super Admin User')
    )

    class Meta:
        ordering = ['-id']

    def __str__(self):
        "String representation of each supervisor setup object"
        return f'{self.user_created} setup for {self.supervisor_user}'
