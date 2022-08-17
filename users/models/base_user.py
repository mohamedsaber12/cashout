from __future__ import unicode_literals

from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFill

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as AbstractUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from disbursement.models import VMTData
from utilities.models import SoftDeletionModel


TYPES = (
    (0, 'Super'),           # when creating super AN EMAIL MUST be created.
    (1, 'Maker'),
    (2, 'Checker'),
    (3, 'Root'),
    (4, 'Uploader'),        # collection only
    (5, 'UpMaker'),         # maker and uploader
    (6, 'InstantAPIChecker'),
    (7, 'InstantAPIViewer'),
    (8, 'Support'),
    (9, 'OnboardUser'),
    (12, 'SuperVisor')
)


class UserManager(AbstractUserManager):
    def get_all_hierarchy_tree(self, hierarchy):
        return self.filter(hierarchy=hierarchy)

    def get_all_makers(self, hierarchy):
        return self.get_all_hierarchy_tree(hierarchy).filter(user_type=1).order_by('level__max_amount_can_be_disbursed')

    def get_all_checkers(self, hierarchy):
        return self.get_all_hierarchy_tree(hierarchy).filter(user_type=2).order_by('level__level_of_authority')


class User(AbstractUser, SoftDeletionModel):
    """
    User model for all the different types of users
    """
    root = models.ForeignKey(
        'users.RootUser',
        on_delete=models.CASCADE,
        null=True
    )
    mobile_no = models.CharField(max_length=16, verbose_name=_('Mobile Number'))
    user_type = models.PositiveSmallIntegerField(choices=TYPES, default=0)
    hierarchy = models.PositiveSmallIntegerField(null=True, db_index=True, default=0)
    email = models.EmailField(blank=False, unique=True, verbose_name=_('Email address'))
    pin = models.CharField(_('pin'), max_length=128, null=True, default='')
    avatar_thumbnail = ProcessedImageField(
        upload_to='avatars',
        processors=[ResizeToFill(100, 100)],
        format='JPEG',
        options={'quality': 60}, null=True, default='avatars/user.png'
    )
    title = models.CharField(max_length=128, default='', null=True, blank=True)
    is_totp_verified = models.BooleanField(null=True, default=False)
    level = models.ForeignKey('users.Levels', related_name='users', on_delete=models.SET_NULL, null=True)
    brand = models.ForeignKey('users.Brand', on_delete=models.SET_NULL, null=True)
    wallet_fees_profile = models.CharField(max_length=30, default='', null=True, blank=True)
    callback_url = models.CharField(max_length=128, default='', null=True, blank=True)
    access_top_up_balance = models.BooleanField(null=True, default=True, verbose_name='Has Access To Top Up Balance')

    objects = UserManager()

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        permissions = (
            ("can_disable_two_factor", "the user can disable two factor"),
            ("can_use_two_factor_backup", "the user can use two factor backup tokens"),
            ("can_use_two_factor", "the user can use two factor"),
            ("has_disbursement", "the client has disbursement options"),
            ("has_collection", "the client has collection options"),
            ("has_instant_disbursement", "the client/his children has instant disbursement capabilities"),
            ("can_view_api_docs", "the user can view the api documentation"),
            ("vodafone_default_onboarding", "the onboarding will be the old one at the super admin and the admin"),
            ("instant_model_onboarding", "the onboarding of an instant entity will be only for the mandatory setups"),
            ("accept_vodafone_onboarding", "the new vf & accept business model of no direct calls to the wallets"),
            (
                "vodafone_facilitator_accept_vodafone_onboarding",
                "like our send business model but can only disburse for vodafone"
            ),
            (
                "banks_standard_model_onboaring",
                "like the vodafone_default_onboarding but with different issuers"
            ),
        )
        ordering = ['-id', '-hierarchy']

    def __str__(self):
        return self.username

    def set_pin(self, raw_pin):
        """Sets pin for every Admin/Root user. Handles hashing formats"""
        self.pin = make_password(raw_pin)
        self.save()

    def check_pin(self, raw_pin):
        """Return a boolean of whether the raw_pin was correct. Handles hashing formats behind the scenes."""
        return check_password(raw_pin, self.pin)

    def children(self):
        """
        If the request is coming from Super user -> Children will be of types (3),
        If the request is coming from Root user -> Children will be of types (1, 2, 6, 7)
        :return: list of children users who belong to that parent
        """
        if self.user_type == 0:
            from .client import Client
            try:
                return [root.client for root in Client.objects.filter(creator=self)]
            except Client.DoesNotExist:
                raise ValidationError("Related user does not exist")

        if self.user_type == 3:
            return User.objects.get_all_hierarchy_tree(self.hierarchy).filter(~Q(user_type=self.user_type))[::1]

        raise ValidationError('This user has no children')

    @property
    def can_view_docs(self):
        """Check if the user has the permission to view the API documentation"""
        if self.is_instantapiviewer or self.has_perm('users.can_view_api_docs') or self.is_instant_model_onboarding:
            return True
        return False

    @property
    def can_disburse(self):
        if self.has_perm('data.can_disburse'):
            return True
        return False

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
    def can_pass_disbursement(self):
        try:
            return self.root.setup.can_pass_disbursement()
        except:
            return False

    @property
    def can_pass_collection(self):
        try:
            return self.root.setup.can_pass_collection()
        except:
            return False

    @cached_property
    def is_root(self):
        return self.user_type == 3

    @cached_property
    def has_access_to_topUp_balance(self):
        return self.access_top_up_balance == True

    @cached_property
    def is_maker(self):
        return self.user_type == 1

    @cached_property
    def is_checker(self):
        return self.user_type == 2

    @cached_property
    def is_uploader(self):
        return self.user_type == 4

    @cached_property
    def is_upmaker(self):
        return self.user_type == 5

    @cached_property
    def is_superadmin(self):
        return self.user_type == 0

    @cached_property
    def is_instantapichecker(self):
        return self.user_type == 6

    @cached_property
    def is_instantapiviewer(self):
        return self.user_type == 7

    @cached_property
    def is_support(self):
        return self.user_type == 8

    @cached_property
    def is_onboard_user(self):
        return self.user_type == 9

    @cached_property
    def is_finance(self):
        return self.user_type == 10

    @cached_property
    def is_finance_with_instant_transaction_view(self):
        return self.user_type == 11

    @cached_property
    def is_supervisor(self):
        return self.user_type == 12

    @cached_property
    def is_instant_member(self):
        """Check if current user belongs to instant cashin family"""
        if self.is_instantapichecker or self.is_instantapiviewer \
                or self.is_instant_model_onboarding or self.has_perm('users.has_instant_disbursement'):
            return True
        return False

    @cached_property
    def get_full_name(self):
        full_name = f"{self.first_name.capitalize()} {self.last_name}"
        return full_name.strip() if full_name.strip() else self

    @property
    def has_vmt_setup(self):
        """Check if this superadmin's vmt credentials setups is completed"""
        if self.is_superadmin and self.vmt:
            return True
        elif self.is_root:
            try:
                return True if self.root.super_admin.vmt else None
            except VMTData.DoesNotExist:
                return False
        return False

    @property
    def has_custom_budget(self):
        """Check if this user has custom budget"""
        from utilities.models import Budget
        try:
            budget = self.budget
            return True
        except Budget.DoesNotExist:
            return False

    def get_absolute_url(self):
        return reverse("users:profile", kwargs={'username': self.username})

    def has_uncomplete_entity_creation(self):
        return self.entity_setups.uncomplete_entity_creations().count() > 0

    def uncomplete_entity_creation(self):
        return self.entity_setups.uncomplete_entity_creations().first()

    def data_type(self):
        DATA_TYPES = {
            'Disbursement': 1,
            'Collection': 2,
            'Both': 3
        }
        if self.has_perm('users.has_disbursement') and self.has_perm('users.has_collection'):
            return DATA_TYPES['Both']
        elif self.has_perm('users.has_disbursement'):
            return DATA_TYPES['Disbursement']
        elif self.has_perm('users.has_collection'):
            return DATA_TYPES['Collection']

    def get_status(self, request):
        data_type = self.data_type()
        if data_type == 3 and (self.is_upmaker or self.is_root):
            return request.session.get('status')
        if data_type == 1 or self.is_maker or self.is_checker or (self.is_root and data_type == 1):
            return 'disbursement'
        if data_type == 2 or self.is_uploader or (self.is_root and data_type == 2):
            return 'collection'

    @cached_property
    def is_vodafone_default_onboarding(self):
        """Check if the current user belongs to vodafone default onboarding setups"""
        if self.has_perm('users.vodafone_default_onboarding'):
            return True
        return False

    @cached_property
    def is_instant_model_onboarding(self):
        """Check if the current user belongs to instant model onboarding setups"""
        if self.has_perm('users.instant_model_onboarding'):
            return True
        return False

    @cached_property
    def is_accept_vodafone_onboarding(self):
        """Check if the current user belongs to accept vodafone onboarding setups"""
        if self.has_perm('users.accept_vodafone_onboarding'):
            return True
        return False

    @cached_property
    def is_vodafone_facilitator_onboarding(self):
        """Check if the current user belongs to vodafone facilitator accept vodafone onboarding setups"""
        if self.has_perm('users.vodafone_facilitator_accept_vodafone_onboarding'):
            return True
        return False

    @cached_property
    def is_banks_standard_model_onboaring(self):
        """
        Check if the current user belongs to
        the banks standard model onboaring setups
        """
        if self.has_perm('users.banks_standard_model_onboaring'):
            return True
        return False
