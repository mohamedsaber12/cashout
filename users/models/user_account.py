from __future__ import unicode_literals

import datetime

import pytz
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q

TYPES = (
    (0, 'Origin'),
    (1, 'Checker'),
    (2, 'Maker')
)


class User(AbstractUser):
    mobile_no = models.CharField(max_length=16, verbose_name='Mobile Number')
    otp = models.CharField(max_length=6, null=True, blank=True)
    user_type = models.PositiveSmallIntegerField(choices=TYPES, default=1)
    hierarchy_id = models.PositiveSmallIntegerField(null=True, db_index=True)
    is_root = models.BooleanField(default=False)
    is_otp_verified = models.BooleanField(default=False)
    verification_time = models.DateTimeField(null=True)

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
    def is_parent(self):
        return self.is_root

    @property
    def parent(self):
        if self.is_root or self.is_superuser:
            return self
        return User.objects.get(hierarchy_id=self.hierarchy_id, is_root=True)

    def child(self):
        return self.brothers()

    @property
    def hierarchy(self):
        return self.hierarchy_id

    def brothers(self):
        return User.objects.filter(Q(hierarchy_id=self.hierarchy_id) & Q(is_root=False))

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

