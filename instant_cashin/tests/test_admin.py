# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase, RequestFactory
from django.contrib.admin.sites import AdminSite
from django.shortcuts import resolve_url
from django.contrib.admin.templatetags.admin_urls import admin_urlname

from users.tests.factories import SuperAdminUserFactory, AdminUserFactory
from users.models import CheckerUser

from instant_cashin.admin import AmanTransactionAdmin, AmanTransactionTypeFilter, InstantTransactionAdmin
from instant_cashin.models import AmanTransaction, InstantTransaction


class MockRequest:
    def get(self):
        request_factory = RequestFactory()
        return request_factory.get("/admin")


class AmanTransactionAdminTests(TestCase):
    def setUp(self):
        super().setUp()
        self.site = AdminSite()
        self.request = MockRequest()
        self.model_admin = AmanTransactionAdmin(AmanTransaction, self.site)
        self.superuser = SuperAdminUserFactory(is_superuser=True)

    # check if aman transaction admin model has add permission
    def test_has_add_permission(self):
        self.request.user = self.superuser
        has_add_permission = self.model_admin.has_add_permission(self.request)
        self.assertFalse(has_add_permission)

    # check if aman transaction admin model has delete permission
    def test_has_delete_permission(self):
        self.request.user = self.superuser
        has_delete_permission = self.model_admin.has_delete_permission(self.request)
        self.assertTrue(has_delete_permission)

    # check if aman transaction admin model has delete permission
    def test_has_delete_permission_with_none_superuser(self):
        self.request.user = SuperAdminUserFactory()
        has_delete_permission = self.model_admin.has_delete_permission(self.request)
        self.assertFalse(has_delete_permission)

    # check if aman transaction admin model has change permission
    def test_has_change_permission(self):
        self.request.user = self.superuser
        has_change_permission = self.model_admin.has_change_permission(self.request)
        self.assertFalse(has_change_permission)

    # test disburser of transaction
    def test_disburser(self):
        checker_user = CheckerUser(id=15, username='test_checker_user')
        instant_trx = InstantTransaction(from_user=checker_user)
        aman_trx_obj = AmanTransaction(transaction=instant_trx)
        self.assertEqual(self.model_admin.disburser(aman_trx_obj), checker_user)

    # test original_transaction_url of transaction
    def test_original_transaction_url(self):
        checker_user = CheckerUser(id=15, username='test_checker_user')
        instant_trx = InstantTransaction(from_user=checker_user)
        aman_trx_obj = AmanTransaction(transaction=instant_trx)
        url = resolve_url(admin_urlname(InstantTransaction._meta, 'change'), aman_trx_obj.transaction.uid)
        self.assertEqual(
            self.model_admin.original_transaction_url(aman_trx_obj),
            f"<a href='{url}'>{aman_trx_obj.transaction.uid}</a>"
        )


class AmanTransactionTypeFilterTests(TestCase):
    def setUp(self):
        self.aman_trx_type_filter = AmanTransactionTypeFilter(
            MockRequest, "manual_transaction", AmanTransaction, AmanTransactionAdmin)

    # test lookups for Aman Transaction Type filter
    def test_lookups(self):
        self.assertEqual(self.aman_trx_type_filter.lookups(
            MockRequest, AmanTransactionAdmin),
            (("manual_transaction", "Disbursement Data Record"),
             ("instant_transaction", "Instant Transaction"))
        )


class InstantTransactionAdminTests(TestCase):

    def setUp(self):
        super().setUp()
        self.site = AdminSite()
        self.request = MockRequest()
        self.model_admin = InstantTransactionAdmin(InstantTransaction, self.site)
        self.superuser = SuperAdminUserFactory(is_superuser=True)

    # check if Instant transaction admin model has add permission
    def test_has_add_permission(self):
        self.request.user = self.superuser
        has_add_permission = self.model_admin.has_add_permission(self.request)
        self.assertFalse(has_add_permission)

    # check if Instant transaction admin model has delete permission
    def test_has_delete_permission(self):
        self.request.user = self.superuser
        has_delete_permission = self.model_admin.has_delete_permission(self.request)
        self.assertFalse(has_delete_permission)

    # check if Instant transaction admin model has change permission
    def test_has_change_permission(self):
        self.request.user = self.superuser
        has_change_permission = self.model_admin.has_change_permission(self.request)
        self.assertFalse(has_change_permission)