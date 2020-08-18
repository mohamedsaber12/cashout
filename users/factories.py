# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory

from faker import Factory as fakeFactory
from django.contrib.auth.models import Permission

from .models import SuperAdminUser


fake = fakeFactory.create()


class BaseUserFactory(factory.django.DjangoModelFactory):
    """
    Base user factory model for creating the mandatory user with its mandatory fields
    """

    username = factory.LazyFunction(fake.user_name)
    password = factory.LazyFunction(fake.password)
    email = factory.LazyFunction(fake.email)
    mobile_no = factory.LazyFunction(fake.numerify)
    first_name = factory.LazyFunction(fake.first_name)
    last_name = factory.LazyFunction(fake.last_name)


class SuperAdminUserFactory(BaseUserFactory):
    """
    Factory model for creating superadmin users
    """

    class Meta:
        model = SuperAdminUser
        abstract = False


class VariousOnboardingSuperAdminUserFactory:
    """
    Factory model for creating superadmin users based on the three business models of onboarding
    """

    @staticmethod
    def default_vodafone():
        """Create superadmin user with the default vodafone onboarding setups permission"""
        superadmin_user = SuperAdminUserFactory()
        superadmin_user.user_permissions.add(
                Permission.objects.get(content_type__app_label='users', codename='vodafone_default_onboarding')
        )
        return superadmin_user

    @staticmethod
    def accept_vodafone():
        """Create superadmin user with the accept vodafone onboarding setups permission"""
        superadmin_user = SuperAdminUserFactory()
        superadmin_user.wallet_fees_profile = "Full"
        superadmin_user.user_permissions.add(
                Permission.objects.get(content_type__app_label='users', codename='accept_vodafone_onboarding')
        )
        return superadmin_user

    @staticmethod
    def instant_apis():
        """Create superadmin user with the instant apis onboarding setups permission"""
        superadmin_user = SuperAdminUserFactory()
        superadmin_user.user_permissions.add(
                Permission.objects.get(content_type__app_label='users', codename='instant_model_onboarding')
        )
        return superadmin_user
