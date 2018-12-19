from __future__ import unicode_literals

import datetime

import pytz
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as AbstractUserManager
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill

TYPES = (
    (0, 'Super'),
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
    mobile_no = models.CharField(max_length=16, verbose_name= _('Mobile Number'))
    user_type = models.PositiveSmallIntegerField(choices=TYPES, default=0)
    hierarchy = models.PositiveSmallIntegerField(
        null=True, db_index=True, default=0)
    verification_time = models.DateTimeField(null=True)
    level = models.ForeignKey(
        'users.Levels', related_name='users', on_delete=models.SET_NULL, null=True)
    email = models.EmailField(blank=False, unique=True, verbose_name=_('Email address'))
    is_email_sent = models.BooleanField(null=True, default=False)
    is_setup_password = models.BooleanField(null=True, default=False)
    avatar_thumbnail = ProcessedImageField(upload_to='avatars',
                                           processors=[ResizeToFill(100, 100)],
                                           format='JPEG',
                                           options={'quality': 60}, null=True, default='user.png')
    title = models.CharField(max_length=128, default='', null=True, blank=True)
    brand = models.ForeignKey(
        'users.Brand', on_delete=models.SET_NULL, null=True)
    is_totp_verified = models.BooleanField(null=True, default=False)
    
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


    @property
    def can_disburse(self):
        if self.has_perm('data.can_disburse'):
            return True
        else:
            return False


    @property
    def root(self):
        if self.is_root:
            return self
        else:
            from users.models import RootUser
            return RootUser.objects.get(hierarchy=self.hierarchy)

    @property
    def super_admin(self):
        if self.is_superadmin:
            return self
        else:
            from users.models import SuperAdminUser
            from users.models import Client
            client = Client.objects.get(client=self.root)
            super_admin = client.creator
            return SuperAdminUser.objects.get(id=super_admin.id)

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

    @cached_property
    def is_superadmin(self):
        return self.user_type == 0

    @cached_property
    def get_full_name(self):
        full_name = '%s %s' % (self.first_name.capitalize(), self.last_name)
        return full_name.strip()

    def get_absolute_url(self):
        return reverse("users:profile")

    def has_uncomplete_entity_creation(self):
        return self.entity_setups.filter(Q(agents_setup=False)).count() > 0

    def uncomplete_entity_creation(self):
        return self.entity_setups.filter(Q(agents_setup=False)).first()
