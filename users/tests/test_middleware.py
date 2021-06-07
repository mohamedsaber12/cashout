from django.http import request
from django.test import RequestFactory

from django.test import TestCase, RequestFactory, Client, override_settings


from users.middleware import EntitySetupCompletionMiddleWare
from mock import patch, Mock
from users.tests.factories import SuperAdminUserFactory
from django.urls import reverse


class MockRequest:
    def get(self):
        request_factory = RequestFactory()
        return request_factory.get("/")

override_settings(MIDDLEWARE_CLASSES=["users.middleware.EntitySetupCompletionMiddleWare"])
class TestEntitySetupCompletionMiddleWare(TestCase):
    
    def setUp(self):
        super().setUp()
        self.request = RequestFactory()
        self.superuser = SuperAdminUserFactory()
        self.client = Client()
        self.client.force_login(self.superuser)

        
     
    def test_init(self):
        ent_middleware = EntitySetupCompletionMiddleWare('response')
        assert(ent_middleware.get_response) == 'response'

    def test_middleware_logout(self):
        req = self.client.get(reverse("users:logout"))
        ent_middleware = EntitySetupCompletionMiddleWare(Mock())
        # CALL MIDDLEWARE ON REQUEST HERE
        ent_middleware(req)
        self.assertEqual(req.status_code, 302)
        self.assertEqual(req.url, "/user/login/")
        
    def test_middleware_client_delete(self):
        req = self.client.post(f"/client/delete/{self.superuser.username}")
        ent_middleware = EntitySetupCompletionMiddleWare(Mock())
        # CALL MIDDLEWARE ON REQUEST HERE
        ent_middleware(req)
        self.assertEqual(req.status_code, 301)
        
    def test_middleware_two_factor_auth_url(self):
        req = self.client.get(reverse("two_factor:profile"))
        ent_middleware = EntitySetupCompletionMiddleWare(Mock())
        # CALL MIDDLEWARE ON REQUEST HERE
        ent_middleware(req)
        self.assertEqual(req.status_code, 200)
        
    
    
        
        
