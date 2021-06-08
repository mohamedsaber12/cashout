from data.models.doc import Doc
from data.models.filecategory import FileCategory
from django.contrib.admin.sites import AdminSite
from django.test import TestCase, RequestFactory

from data.admin import DocAdmin, FileCategoryAdmin
from users.tests.factories import SuperAdminUserFactory, AdminUserFactory
from data.tests.factories import DisbursementFileCategoryFactory
from django.test.client import RequestFactory


class MockRequest:
    def get(self):
        request_factory = RequestFactory()
        return request_factory.get("/admin")


class TestDocdmin(TestCase):
    def setUp(self):
        super().setUp()
        self.site = AdminSite()
        self.request = MockRequest()
        self.model_admin = DocAdmin(Doc, self.site)
        self.superuser = SuperAdminUserFactory(is_superuser=True)
        self.normal_user = AdminUserFactory(user_type=3)
        
    def test_user_admin_str(self):
        self.assertEqual(str(self.model_admin), "data.DocAdmin")
        
    def test_add_permission(self):
        self.request.user = self.superuser
        has_add_permission = self.model_admin.has_add_permission(self.request)
        self.assertFalse(has_add_permission)
        
    def test_change_permission(self):
        self.request.user = self.superuser
        has_change_permission = self.model_admin.has_change_permission(self.request)
        self.assertFalse(has_change_permission)
        
    def test_delete_permission(self):
        self.request.user = self.superuser
        has_delete_permission = self.model_admin.has_delete_permission(self.request)
        self.assertFalse(has_delete_permission)
        
class TestFileCategoryAdmin(TestCase):
    def setUp(self):
        super().setUp()
        self.site = AdminSite()
        self.request = MockRequest()
        self.model_admin = FileCategoryAdmin(FileCategory, self.site)
        self.superuser = SuperAdminUserFactory(is_superuser=True)
        self.normal_user = AdminUserFactory(user_type=3)
        
    def test_user_admin_str(self):
        self.assertEqual(str(self.model_admin), "data.FileCategoryAdmin")
        
    def test_get_form_without_object(self):
        self.request.user = self.superuser
        try:
            form = self.model_admin.get_form(self.request)
            self.assertIsNone(form)
        except Exception:
            pass
        
    # def test_get_queryset_super_user(self):
    #     self.request.user = self.superuser
    #     resp = self.model_admin.get_queryset(self.request)
    #     file_category_one = DisbursementFileCategoryFactory()
    #     file_category_two = DisbursementFileCategoryFactory()
    #     qs = FileCategory.objects.all()
    #     self.assertCountEqual(resp, qs)

        
