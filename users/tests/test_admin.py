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
        
    def test_export_report(self):
        request_factory = self.request.post("/", {"apply": True,"start_date": "2010-02-01", "end_date": "2010-02-20"})
                            
        request_factory.user = self.superuser
        
        resp = self.model_admin.export_report(request_factory, SuperAdminUser.objects.all())
        self.assertEqual(resp.status_code, 200)

    
    
    # def test_has_module_permission(self):
    #     # test superuser has_module_permission
    #     self.request.user = self.superuser
    #     has_module_permission = self.model_admin.has_module_permission(self.request)
    #     self.assertTrue(has_module_permission)
    #     # test community super admin has_module_permission
    #     self.request.user = self.community_superadmin
    #     has_module_permission = self.model_admin.has_module_permission(self.request)
    #     self.assertFalse(has_module_permission)
    #     # test community admin has_module_permission
    #     self.request.user = self.communityadmin
    #     has_module_permission = self.model_admin.has_module_permission(self.request)
    #     self.assertFalse(has_module_permission)

    # def test_get_form(self):
    #     # we are trying to access a form that never exists
    #     self.request.user = self.superuser
    #     try:
    #         form = self.model_admin.get_form(self.request)
    #         self.assertIsNone(form)
    #     except Exception:
    #         pass


# class TestCommunityAdmin(TestCase):
#     def setUp(self):
#         super().setUp()
#         self.site = AdminSite()
#         self.request = MockRequest()
#         self.model_admin = CommunityAdminAdmin(CommunityAdmin, self.site)
#         self.community = CommunityFactory()
#         self.superuser = UserFactory(is_superuser=True)
#         self.communityadmin = CommunityAdminFactory()
#         community_admin_modules = ["Membership", "SubMembership"]
#         self.community_superadmin = CommunitySuperAdminFactory(
#             community=self.community, communtiy_admin_modules=community_admin_modules
#         )
#         self.add_fields = [
#             "name",
#             "username",
#             "email",
#             "is_community_admin",
#             "receive_payment_updates",
#             "communtiy_admin_modules",
#             "is_community_super_admin",
#             "community",
#             "enable_refund_void_actions",
#         ]
#         self.change_fields = [
#             "name",
#             "username",
#             "email",
#             "is_community_admin",
#             "receive_payment_updates",
#             "communtiy_admin_modules",
#             "is_community_super_admin",
#             "community",
#             "enable_refund_void_actions",
#         ]
#         self.read_only_fields = ["last_login", "date_joined"]
#         self.admin_actions = (CommunityAdminAdmin.bulk_send_rest_password_email,)

#     def test_communityadminadmin_str(self):
#         self.assertEqual(str(self.model_admin), "users.CommunityAdminAdmin")

#     def test_add_communityadmin_fields(self):
#         self.request.user = self.superuser
#         add_fieldsets = self.model_admin.get_fieldsets(self.request)
#         self.assertEqual(list(add_fieldsets[0][1]["fields"]), self.add_fields)

#     def test_change_communityadmin_fields(self):
#         self.request.user = self.superuser
#         # test add community admin form
#         add_fieldsets = self.model_admin.get_fieldsets(self.request)
#         self.assertEqual(list(add_fieldsets[0][1]["fields"]), self.add_fields)
#         # test change community admin form
#         change_fieldsets = self.model_admin.get_fieldsets(
#             self.request, self.communityadmin
#         )
#         # None, Important dates
#         change_fields = list(change_fieldsets[0][1]["fields"])
#         self.assertEqual(change_fields, self.change_fields)

#     def test_read_only_fields(self):
#         self.request.user = self.superuser
#         read_only_fields = list(
#             self.model_admin.get_readonly_fields(self.request, self.communityadmin)
#         )
#         self.assertEqual(read_only_fields, self.read_only_fields)

#     def test_has_module_permission(self):
#         # test community super admin has_module_permission
#         self.request.user = self.community_superadmin
#         has_module_permission = self.model_admin.has_module_permission(self.request)
#         self.assertTrue(has_module_permission)
#         # test community admin has_module_permission
#         self.request.user = self.communityadmin
#         has_module_permission = self.model_admin.has_module_permission(self.request)
#         self.assertFalse(has_module_permission)

#     def test_communtiy_admin_modules_choices(self):
#         self.request.user = self.community_superadmin
#         # fields = self.model_admin.get_fields(self.request)
#         # for i, val in enumerate(fields):
#         #     if not val == "is_community_admin":
#         #         continue

#         #     self.assertEquals(
#         #         fields[i].choices,
#         #         get_community_admin_modules(self.request.user.communtiy_admin_modules),
#         #     )
#         #     break
#         community = CommunityFactory()
#         community_admin = CommunityAdmin()
#         community_admin.name = "test_admin"
#         community_admin.username = "+201100011110"
#         community_admin.email = "ba@test.test"
#         community_admin.community = community
#         community_admin.communtiy_admin_modules = ["Bill", "BillInvoice"]
#         try:
#             self.model_admin.save_model(
#                 self.request, community_admin, change=None, form=None
#             )
#         except ValidationError as e:
#             self.assertEqual(
#                 str(e),
#                 "['Community admin should have access to modules already assigned to this community super admin!']",
#             )
#         community_admin.communtiy_admin_modules = ["Membership", "SubMembership"]
#         self.model_admin.save_model(
#             self.request, community_admin, change=None, form=None
#         )
#         ca = CommunityAdmin.objects.get(username="+201100011110")
#         self.assertEquals(
#             ca.communtiy_admin_modules, self.request.user.communtiy_admin_modules,
#         )

#     def test_community_super_admin_creation_per_community(self):
#         self.request.user = self.superuser
#         # each community should have only one super admin
#         community = CommunityFactory()
#         csa = CommunityAdminFactory(community=community)
#         self.assertIsNotNone(csa)
#         community = CommunityFactory()
#         community_super_admin = CommunityAdmin()
#         community_super_admin.name = "test_sa"
#         community_super_admin.username = "+201100011200"
#         community_super_admin.email = "sa@test.test"
#         community_super_admin.is_community_admin = True
#         community_super_admin.is_community_super_admin = True
#         community_super_admin.community = community
#         try:
#             self.model_admin.save_model(
#                 self.request, community_super_admin, change=None, form=None
#             )
#         except ValidationError as e:
#             self.assertEqual(str(e), "['Community should have only one super admin!']")

#     @mock.patch(
#         "community_backend.users.admin.notify.send_community_admin_reset_password"
#     )
#     def test_user_save_model_is_community_admin(
#         self, mocked_send_community_admin_reset_password
#     ):
#         self.request.user = self.superuser
#         community = CommunityFactory()
#         community_admin = CommunityAdmin()
#         community_admin.name = "test"
#         community_admin.username = "+201100011100"
#         community_admin.email = "test@test.test"
#         community_admin.is_community_admin = True
#         community_admin.community = community
#         self.model_admin.save_model(
#             self.request, community_admin, form=None, change=None
#         )
#         mocked_send_community_admin_reset_password.assert_called()

#     @mock.patch(
#         "community_backend.users.admin.notify.send_community_admin_reset_password"
#     )
#     def test_user_change_save_model_not_community_admin(
#         self, mocked_send_community_admin_reset_password
#     ):
#         self.request.user = self.superuser
#         community = CommunityFactory()
#         community_admin = CommunityAdmin()
#         community_admin.name = "Updated test name"
#         community_admin.username = "+201100011101"
#         community_admin.email = "test@test.test"
#         community_admin.community = community
#         community_admin.is_community_admin = False
#         self.model_admin.save_model(
#             self.request, community_admin, form=None, change=True
#         )
#         mocked_send_community_admin_reset_password.assert_not_called()

#     def test_community_admin_with_and_without_community(self):
#         self.request.user = self.superuser
#         community_admin = CommunityAdmin()
#         community_admin.name = "test_admin_without_community"
#         community_admin.username = "+201100011111"
#         community_admin.email = "no-community@test.test"
#         community_admin.is_community_admin = True
#         try:
#             self.model_admin.save_model(
#                 self.request, community_admin, form=None, change=True
#             )
#         except ValidationError as e:
#             self.assertEqual(str(e), "['Community admin should have a community!']")
#         community = CommunityFactory()
#         community_admin.community = community
#         self.model_admin.save_model(
#             self.request, community_admin, form=None, change=True
#         )
#         ca = CommunityAdmin.objects.get(username="+201100011111")
#         self.assertEqual(community, ca.community)

#     def test_community_admin_with_and_without_email(self):
#         self.request.user = self.superuser
#         community = CommunityFactory()
#         community_admin = CommunityAdmin()
#         community_admin.name = "test_admin"
#         community_admin.username = "+201100011112"
#         community_admin.community = community
#         community_admin.is_community_admin = True
#         try:
#             self.model_admin.save_model(
#                 self.request, community_admin, form=None, change=True
#             )
#         except ValidationError as e:
#             self.assertEqual(str(e), "['Community admin should have an email!']")

#         community_admin.email = "email@test.test"
#         self.model_admin.save_model(
#             self.request, community_admin, form=None, change=True
#         )
#         ca = CommunityAdmin.objects.get(username="+201100011112")
#         self.assertIsNotNone(ca.email)
#         self.assertEqual(ca.email, "email@test.test")

#     def test_superuser_actions(self):
#         self.request.user = self.superuser
#         self.assertEqual(self.model_admin.actions, self.admin_actions)

#     def test_community_admin_actions(self):
#         self.request.user = self.community_superadmin
#         self.assertEqual(self.model_admin.actions, self.admin_actions)
