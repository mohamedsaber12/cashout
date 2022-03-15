# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random

import factory
from faker import Factory as fakeFactory

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Permission

from disbursement.factories import VariousAgentFactory, VMTDataFactory

from users.models import (
    SuperAdminUser, RootUser, MakerUser, CheckerUser, Client,
    InstantAPICheckerUser, InstantAPIViewerUser
)


fake = fakeFactory.create()


class BaseUserFactory(factory.django.DjangoModelFactory):
    """
    Base user factory model for creating the mandatory user with its mandatory fields
    """

    username = factory.LazyFunction(fake.user_name)
    password = factory.Sequence(lambda obj: make_password(fake.password))
    email = factory.LazyFunction(fake.email)
    mobile_no = factory.Sequence(lambda obj: fake.numerify(text="010########"))
    first_name = factory.LazyFunction(fake.first_name)
    last_name = factory.LazyFunction(fake.last_name)


class SuperAdminUserFactory(BaseUserFactory):
    """
    Factory model for creating super admin users
    """

    class Meta:
        model = SuperAdminUser
        abstract = False


class VariousOnboardingSuperAdminUserFactory:
    """
    Factory model for creating superadmin users based on the three business models of onboarding
    """

    @classmethod
    def create_new_superadmin(cls):
        superadmin_user = SuperAdminUserFactory()
        VMTDataFactory(vmt=superadmin_user)
        return superadmin_user

    @staticmethod
    def default_vodafone():
        """Create superadmin user with the default vodafone onboarding setups permission"""
        superadmin_user = VariousOnboardingSuperAdminUserFactory.create_new_superadmin()
        superadmin_user.user_permissions.add(
            Permission.objects.get(content_type__app_label="users", codename="vodafone_default_onboarding")
        )
        return superadmin_user

    @staticmethod
    def accept_vodafone():
        """Create superadmin user with the accept vodafone onboarding setups permission"""
        superadmin_user = VariousOnboardingSuperAdminUserFactory.create_new_superadmin()
        VariousAgentFactory.mandatory_agents(agent_provider=superadmin_user)
        superadmin_user.wallet_fees_profile = random.choice(["Full", "Half", "No fees"])
        superadmin_user.user_permissions.add(
            Permission.objects.get(content_type__app_label="users", codename="accept_vodafone_onboarding")
        )
        superadmin_user.save()
        return superadmin_user

    @staticmethod
    def instant_apis():
        """Create superadmin user with the instant apis onboarding setups permission"""
        superadmin_user = VariousOnboardingSuperAdminUserFactory.create_new_superadmin()
        VariousAgentFactory.mandatory_agents(agent_provider=superadmin_user)
        superadmin_user.user_permissions.add(
            Permission.objects.get(content_type__app_label="users", codename="instant_model_onboarding")
        )
        superadmin_user.save()
        return superadmin_user

    @staticmethod
    def vodafone_facilitator():
        """Create superadmin user with vodafone facilitator onboarding setups permission"""
        superadmin_user = VariousOnboardingSuperAdminUserFactory.create_new_superadmin()
        VariousAgentFactory.mandatory_agents(agent_provider=superadmin_user)
        superadmin_user.wallet_fees_profile = random.choice(["Full", "Half", "No fees"])
        superadmin_user.user_permissions.add(
            Permission.objects.get(content_type__app_label="users", codename="vodafone_facilitator_accept_vodafone_onboarding")
        )
        superadmin_user.save()
        return superadmin_user

    @staticmethod
    def banks_standard():
        """Create superadmin user with the bank standard onboarding setups permission"""
        superadmin_user = VariousOnboardingSuperAdminUserFactory.create_new_superadmin()
        VariousAgentFactory.mandatory_agents(agent_provider=superadmin_user)
        superadmin_user.wallet_fees_profile = random.choice(["Full", "Half", "No fees"])
        superadmin_user.user_permissions.add(
                Permission.objects.get(content_type__app_label="users", codename="banks_standard_model_onboaring")
        )
        superadmin_user.save()
        return superadmin_user


class AdminUserFactory(BaseUserFactory):
    """
    Factory model for creating admin users
    """

    class Meta:
        model = RootUser
        abstract = False


class MakerUserFactory(BaseUserFactory):
    """
    Factory model for creating maker users
    """

    class Meta:
        model = MakerUser
        abstract = False


class CheckerUserFactory(BaseUserFactory):
    """
    Factory model for creating checker users
    """

    class Meta:
        model = CheckerUser
        abstract = False


class InstantAPICheckerFactory(BaseUserFactory):
    """
    Factory model for creating checker users
    """

    class Meta:
        model = InstantAPICheckerUser
        abstract = False

class InstantAPIViewerUserFactory(BaseUserFactory):
    """
    Factory model for creating checker users
    """

    class Meta:
        model = InstantAPIViewerUser
        abstract = False


class ClientUserFactory(factory.django.DjangoModelFactory):

    is_active = factory.LazyFunction(fake.boolean)
    fees_percentage = factory.LazyFunction(fake.numerify)
    vodafone_facilitator_identifier = factory.Sequence(lambda obj: fake.numerify(text="##########"))
    custom_profile = ''
    smsc_sender_name = factory.LazyFunction(fake.first_name)
    agents_onboarding_choice = factory.Iterator(Client.AGENTS_ONBOARDING_CHOICES)


    client = factory.RelatedFactory(
        AdminUserFactory,
        factory_related_name='client',
    )
    creator = factory.RelatedFactory(
        SuperAdminUserFactory,
        factory_related_name='clients'
    )
