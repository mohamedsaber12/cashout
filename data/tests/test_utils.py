from users.tests.factories import SuperAdminUserFactory, CheckerUserFactory
from django.test import TestCase
from data.tests.factories import FormarFactory, FileDataFactory, DocFactory
from data.models.category_data import Format
from data.models.file_data import FileData
from unittest import mock
from data.utils import validate_file_extension, get_client_ip
from django.test.client import RequestFactory


class Value:
        def __init__(self, name):
            self.name = name
            
class MockRequest:
    def get(self):
        request_factory = RequestFactory()
        return request_factory.get("/")
            
            
class TestUtils(TestCase):
    
    def test_validate_file_extension_function(self):
        data = Value("test.tex")
        with self.assertRaises(Exception) as context:
            validate_file_extension(data)
            self.assertTrue('Error message' in context.exception)
            print(context.exception)
            
    def test_get_client_ip(self):
        req = RequestFactory()
        req.META["HTTP_X_FORWARDED_FOR"] = "test"
        resp = get_client_ip(req)
        
        
        
