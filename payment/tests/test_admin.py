from django.contrib.admin.sites import AdminSite
from django.test import TestCase, RequestFactory

from payment.admin import TransactionsAdmin
from users.tests.factories import SuperAdminUserFactory, AdminUserFactory
from payment.models import Transactions
from django.test.client import RequestFactory


class MockRequest:
    def get(self):
        request_factory = RequestFactory()
        return request_factory.get("/admin")


class TestTransactionsAdmin(TestCase):
    def setUp(self):
        super().setUp()
        self.site = AdminSite()
        self.request = MockRequest()
        self.model_admin = TransactionsAdmin(Transactions, self.site)
        self.superuser = SuperAdminUserFactory(is_superuser=True)
        self.normal_user = AdminUserFactory(user_type=3)
        
    def test_get_url(self):
        resp = self.request.get()
        self.assertEqual(resp.path, '/admin')
        
    def test_change_permission(self):
        self.request.user = self.superuser
        has_change_permission = self.model_admin.has_change_permission(self.request)
        self.assertFalse(has_change_permission)
        
    def test_add_permission(self):
        self.request.user = self.superuser
        has_change_permission = self.model_admin.has_add_permission(self.request)
        self.assertFalse(has_change_permission)
        
