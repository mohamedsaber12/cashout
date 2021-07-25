# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from users.models import Brand
from users.tests.factories import SuperAdminUserFactory, AdminUserFactory
from utilities.tasks import generate_onboarded_entities_report, send_transfer_request_email


class OnboardedEntitiesReportTests(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()

    def test_generate_onboarded_entities_report(self):
        self.assertEqual(
            generate_onboarded_entities_report([], self.super_admin.username),
            0
        )


class TransferRequestEmailTests(TestCase):

    def setUp(self):
        self.root = AdminUserFactory(user_type=3)
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.root = self.root
        self.root.brand = self.brand
        self.root.save()

    def test_send_transfer_request_email(self):
        self.assertTrue(
            send_transfer_request_email(self.root.username, "test transfer request")
        )
