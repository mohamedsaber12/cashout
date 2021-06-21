from data.models.doc import Doc
from django.contrib.admin.sites import AdminSite
from django.test import TestCase, RequestFactory

from users.tests.factories import SuperAdminUserFactory, AdminUserFactory
from django.test.client import RequestFactory
from data.views import redirect_home
import requests

class MockRequest:
    def get(self):
        request_factory = RequestFactory()
        return request_factory.get("/admin/")
    
    
# class TestDataViews(TestCase):
#     def setUp(self):
#         self.superuser = SuperAdminUserFactory(is_superuser=True)
#         self.normal_user = AdminUserFactory(user_type=3)
#         self.request = requests.get("http://www.google.com")
        
#     def test_redirect_home_with_no_user(self):
#         resp = redirect_home(self.request)
        