from __future__ import unicode_literals

import datetime

import pytz
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as AbstractUserManager
from django.db import models
from django.db.models import Q
from django.utils.functional import cached_property
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill

TYPES = (
    (0, 'Super')
    (1, 'Maker'),
    (2, 'Checker'),
    (3, 'Root'),
)


class UserManager(AbstractUserManager):
    def get_all_hierarchy_tree(self, hierarchy):
        return self.filter(hierarchy=hierarchy)

    def get_all_makers(self, hierarchy):
        return self.get_all_hierarchy_tree(hierarchy).filter(user_type=1).order_by('max_amount_can_be_disbursed')

    def get_all_checkers(self, hierarchy):
        return self.get_all_hierarchy_tree(hierarchy).filter(user_type=2).order_by('level__level_of_authority')


class User(AbstractUser):
    mobile_no = models.CharField(max_length=16, verbose_name='Mobile Number')
    otp = models.CharField(max_length=6, null=True, blank=True)
    user_type = models.PositiveSmallIntegerField(choices=TYPES, default=0)
    hierarchy = models.PositiveSmallIntegerField(
        null=True, db_index=True, default=0)
    is_otp_verified = models.BooleanField(default=False)
    verification_time = models.DateTimeField(null=True)
    level = models.ForeignKey(
        'users.Levels', related_name='users', on_delete=models.SET_NULL, null=True)
    email = models.EmailField('email address', blank=False)
    is_email_sent = models.BooleanField(null=True, default=False)
    is_setup_password = models.BooleanField(null=True, default=False)
    avatar_thumbnail = ProcessedImageField(upload_to='avatars',
                                           processors=[ResizeToFill(100, 100)],
                                           format='JPEG',
                                           options={'quality': 60}, null=True, default='pp.jpeg')

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

    def child(self):
        return User.objects.filter(Q(hierarchy=self.hierarchy) & ~Q(user_type=3))

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
            diff = datetime.datetime.utcnow().replace(
                tzinfo=pytz.UTC) - self.verification_time
            if diff.total_seconds() < 1800 and self.is_otp_verified:
                return True
        except TypeError:
            return False
        return False

    def otp_verify(self):
        self.verification_time = datetime.datetime.now()
        self.is_otp_verified = True
        self.save()

    @property
    def root(self):
        if self.is_root:
            return self
        else:
            from users.models import RootUser
            return RootUser.objects.get(hierarchy=self.hierarchy)

    @property
    def can_pass(self):
        return self.root.setup.can_pass()

    @cached_property
    def is_root(self):
        return self.user_type == 3

    @cached_property
    def is_maker(self):
        return self.user_type == 1

    @cached_property
    def is_checker(self):
        return self.user_type == 2
