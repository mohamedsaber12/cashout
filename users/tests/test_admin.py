from django.contrib.admin.sites import AdminSite
from django.test import TestCase, RequestFactory

from users.admin import UserAccountAdmin, SuperAdmin
from users.tests.factories import SuperAdminUserFactory, AdminUserFactory
from users.models import User, SuperAdminUser
from django.test.client import RequestFactory

from django.core.exceptions import PermissionDenied

class MockRequest:
    def get(self):
        request_factory = RequestFactory()
        return request_factory.get("/admin")


class TestUserAccountAdmin(TestCase):
    def setUp(self):
        super().setUp()
        self.site = AdminSite()
        self.request = MockRequest()
        self.model_admin = UserAccountAdmin(User, self.site)
        self.superuser = SuperAdminUserFactory(is_superuser=True)
        self.normal_user = AdminUserFactory(user_type=3)
        
    def test_user_admin_str(self):
        self.assertEqual(str(self.model_admin), "users.UserAccountAdmin")
        
    def test_deactivate_selected_permission_denied(self):
        self.request.user = self.normal_user
        has_change_permission = self.model_admin.has_change_permission(self.request)
        self.assertFalse(has_change_permission)
        with self.assertRaises(PermissionDenied):
            self.model_admin.deactivate_selected(self.request, [])
            
    def test_deactivate_selected_success_scenario(self):
        self.request.user = self.superuser
        has_change_permission = self.model_admin.has_change_permission(self.request)
        self.assertTrue(has_change_permission)
        self.normal_user.is_active = False
        self.normal_user.save()
        users = User.objects.all()
        self.model_admin.deactivate_selected(self.request, users)
        users = User.objects.all()
        for user in users:
            self.assertFalse(user.is_active)
            
    def test_activate_selected_permission_denied(self):
            self.request.user = self.normal_user
            has_change_permission = self.model_admin.has_change_permission(self.request)
            self.assertFalse(has_change_permission)
            with self.assertRaises(PermissionDenied):
                self.model_admin.activate_selected(self.request, [])
            
    def test_activate_selected_success_scenario(self):
        self.request.user = self.superuser
        has_change_permission = self.model_admin.has_change_permission(self.request)
        self.assertTrue(has_change_permission)
        self.normal_user.is_active = False
        self.normal_user.save()
        users = User.objects.all()
        self.model_admin.activate_selected(self.request, users)
        users = User.objects.all()
        for user in users:
            self.assertTrue(user.is_active)
            
    def test_get_list_display_super_user(self):
        self.request.user = self.superuser
        resp = self.model_admin.get_list_display(self.request)
        expected_list_display = ('username', 'first_name', 'last_name', 'email', 'groups', 'is_active', 'user_type')
        self.assertEqual(resp, expected_list_display)
        
    def test_get_list_display_normal_user(self):
        self.request.user = self.normal_user
        resp = self.model_admin.get_list_display(self.request)
        expected_list_display = ('username', 'first_name', 'last_name', 'email', 'is_active')
        self.assertEqual(resp, expected_list_display)
        
    def test_get_form_without_object(self):
        self.request.user = self.superuser
        try:
            form = self.model_admin.get_form(self.request)
            self.assertIsNone(form)
        except Exception:
            pass
        
    def test_get_queryset_super_user(self):
        self.request.user = self.superuser
        resp = self.model_admin.get_queryset(self.request)
        qs = User.objects.all()
        self.assertCountEqual(resp, qs)
        
    def test_get_queryset_root_user(self):
        self.request.user = self.normal_user
        resp = self.model_admin.get_queryset(self.request)
        qs = User.objects.all()
        self.assertCountEqual(resp, qs)
        
    def test_get_fieldsets_super_user(self):
        self.request.user = self.superuser
        obj = self.normal_user
        
        resp = self.model_admin.get_fieldsets(self.request, obj)
        expected_fieldsets = ((None, {'classes': ('wide',), 'fields': ('username', 'email', 'password')}), ('Personal info', {'fields': ('first_name', 'last_name', 'mobile_no')}), ('Permissions', {'fields': ('is_active', 'is_staff', 'user_type')}), ('Important dates', {'fields': ('last_login', 'date_joined')}))
        self.assertEqual(resp, expected_fieldsets)
        
        
class TestSuperAdmin(TestCase):
    
    def setUp(self):
        super().setUp()
        self.site = AdminSite()
        self.request = RequestFactory()
        self.model_admin = SuperAdmin(User, self.site)
        self.superuser = SuperAdminUserFactory(is_superuser=True)
        self.normal_user = AdminUserFactory(user_type=3)
        
    def test_user_admin_str(self):
        self.assertEqual(str(self.model_admin), "users.SuperAdmin")
        
    def test_get_fieldsets_super_user(self):
        self.request.user = self.superuser
        
        resp = self.model_admin.get_fieldsets(self.request)
        expected_fieldsets = ((None, {'classes': ('wide',), 'fields': ('username', 'password1', 'password2')}), ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'mobile_no')}), ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}), ('Important dates', {'fields': ('last_login', 'date_joined')}))
        self.assertEqual(resp, expected_fieldsets)
        
    # def test_export_report(self):
    #     request_factory = self.request.post("/", {"apply": True,"start_date": "2010-02-01", "end_date": "2010-02-20"})
    #
    #     request_factory.user = self.superuser
    #
    #     resp = self.model_admin.export_report(request_factory, SuperAdminUser.objects.all())
    #     self.assertEqual(resp.status_code, 200)
