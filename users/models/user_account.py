from __future__ import unicode_literals

import datetime

import pytz
from django.contrib.auth.models import AbstractUser, UserManager as AbstractUserManager
from django.db import models
from django.db.models import Q

TYPES = (
    (1, 'Maker'),
    (2, 'Checker'),
)


class UserManager(AbstractUserManager):
    def get_all_hierarchy_tree(self, hierarchy):
        return self.filter(hierarchy=hierarchy)

    def get_all_makers(self, hierarchy):
        return self.get_all_hierarchy_tree(hierarchy).filter(user_type=1).order_by('max_amount_can_be_disbursed')

    def get_all_checkers(self, hierarchy):
        return self.get_all_hierarchy_tree(hierarchy).filter(user_type=2).order_by('level_of_authority')

    def create_maker(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('user_type', 1)
        extra_fields.setdefault('is_superuser', False)
        if 'hierarchy' not in extra_fields:
            raise ValueError('The given hierarchy must be set')
        return self._create_user(username, email, password, **extra_fields)

    def create_checker(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('user_type', 1)
        extra_fields.setdefault('is_superuser', False)
        if 'hierarchy' not in extra_fields:
            raise ValueError('The given hierarchy must be set')
        return self._create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    mobile_no = models.CharField(max_length=16, verbose_name='Mobile Number')
    otp = models.CharField(max_length=6, null=True, blank=True)
    user_type = models.PositiveSmallIntegerField(choices=TYPES, default=1)
    hierarchy = models.PositiveSmallIntegerField(null=True, db_index=True)
    is_parent = models.BooleanField(default=False)
    is_otp_verified = models.BooleanField(default=False)
    verification_time = models.DateTimeField(null=True)
    is_setup_complete = models.BooleanField(default=False)
    level = models.ForeignKey('users.Levels', related_name='users', on_delete=models.SET_NULL, null=True)
    objects = UserManager()

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        permissions = (
            ("can_disable_two_factor", "the user can disable two factor"),
            ("can_use_two_factor_backup", "the user can use two factor backup tokens"),
            ("can_use_two_factor", "the user can use two factor"),
        )

    def __str__(self):  # __unicode__ for Python 2
        return str(self.username)

    @property
    def parent(self):
        if self.is_parent or self.is_superuser:
            return self
        return User.objects.get(hierarchy_id=self.hierarchy, is_parent=True)

    def child(self):
        return User.objects.filter(Q(hierarchy_id=self.hierarchy) & Q(is_parent=False))

    def clean_otp(self):
        self.otp = None
        self.save()
        return 'cleaned'

    @property
    def can_disburse(self):
        if self.has_perm('data.can_disburse'):
            return True
        else:
            return False

    def check_verification(self, otp_method):
        if otp_method == '3':
            return True
        try:
            diff = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC) - self.verification_time
            if diff.total_seconds() < 1800 and self.is_otp_verified:
                return True
        except TypeError:
            return False
        return False

    def otp_verify(self):
        self.verification_time = datetime.datetime.now()
        self.is_otp_verified = True
        self.save()
