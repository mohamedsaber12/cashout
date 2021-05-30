# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from users.tests.factories import VariousOnboardingSuperAdminUserFactory


class ModelTests(TestCase):
    """
    Tests for the users application models
    """

    def test_successful_creating_default_vodafone_superadmin(self):
        """Test successfully creating superadmin user with default vodafone onboarding permissions"""
        superadmin = VariousOnboardingSuperAdminUserFactory.default_vodafone()
        self.assertEqual(superadmin.username, str(superadmin))
        self.assertTrue(superadmin.is_superadmin)
        self.assertEqual(superadmin, superadmin.vmt.vmt)
        self.assertTrue(superadmin.has_perm("users.vodafone_default_onboarding"))
        self.assertEqual(superadmin.agents.all().count(), 0)

    def test_successful_creating_accept_vodafone_superadmin(self):
        """Test successfully creating superadmin user with accept vodafone onboarding permissions"""
        superadmin = VariousOnboardingSuperAdminUserFactory.accept_vodafone()
        self.assertEqual(superadmin.username, str(superadmin))
        self.assertTrue(superadmin.is_superadmin)
        self.assertEqual(superadmin, superadmin.vmt.vmt)
        self.assertTrue(superadmin.has_perm("users.accept_vodafone_onboarding"))
        self.assertIn(superadmin.wallet_fees_profile, ["Full", "Half", "No fees"])
        self.assertGreaterEqual(superadmin.agents.all().count(), 3)

    def test_successful_creating_instant_superadmin(self):
        """Test successfully creating superadmin user with instant onboarding permissions"""
        superadmin = VariousOnboardingSuperAdminUserFactory.instant_apis()
        self.assertEqual(superadmin.username, str(superadmin))
        self.assertTrue(superadmin.is_superadmin)
        self.assertEqual(superadmin, superadmin.vmt.vmt)
        self.assertTrue(superadmin.has_perm("users.instant_model_onboarding"))
        self.assertGreaterEqual(superadmin.agents.all().count(), 3)
