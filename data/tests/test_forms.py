from data.models import filecategory
from django.http import request
from django.test import RequestFactory

from django.test import TestCase, RequestFactory, Client, override_settings


from users.middleware import EntitySetupCompletionMiddleWare
from mock import patch, Mock
from users.tests.factories import SuperAdminUserFactory
from django.urls import reverse
from data.forms import FileDocumentForm
from data.tests.factories import DocFactory
from PIL import Image
from io import BytesIO

from django.core.files.base import ContentFile


class MockRequest:
    def get(self):
        request_factory = RequestFactory()
        return request_factory.get("/")
    
    
class TestFileDocumentForm(TestCase):
    def setUp(self):
        super().setUp()
        self.request = MockRequest()
        self.superuser = SuperAdminUserFactory(is_superuser=True)
    
    def test_file_doc_form_validate_file_type(self):
        form = FileDocumentForm(request={'request': "test"})
        image_file = BytesIO()
        image = Image.new('RGBA', size=(50,50), color=(256,0,0))
        image.save(image_file, 'png')
        image_file.seek(0)

        # django_friendly_file = ContentFile(image_file.read(), 'test.png')

        # resp = form._validate_file_type(image_file)
        # print(resp)
        
