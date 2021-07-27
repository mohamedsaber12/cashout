from django.test import RequestFactory
from django.test import TestCase, RequestFactory
from users.tests.factories import SuperAdminUserFactory
from data.forms import FileDocumentForm
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile



from rest_framework.test import APIClient, APITestCase
from users.tests.factories import SuperAdminUserFactory
from django.urls import reverse
from rest_framework import status


class TestFileDocumentForm(APITestCase):
                
    # test new_amount validation
    def test_validate_form(self):
        im = Image.new(mode='RGB', size=(200, 200))
        im_io = BytesIO()
        im.save(im_io, 'JPEG')
        im_io.seek(0)

        file = InMemoryUploadedFile(
            im_io, None, 'random-name.jpg', 'image/jpeg', len(im_io.getvalue()), None
        )
        file_doc_form = FileDocumentForm(
            data={"file": file},
            request={"test": "test"}
        )
        self.assertEqual(file_doc_form.is_valid(), False)
           
    def test_validate_file_type(self):
        im = Image.new(mode='RGB', size=(200, 200))
        im_io = BytesIO()
        im.save(im_io, 'JPEG')
        im_io.seek(0)

        file = InMemoryUploadedFile(
            im_io, None, 'random-name.jpg', 'image/jpeg', len(im_io.getvalue()), None
        )
        file_doc_form = FileDocumentForm(
            data={"file": file},
            request={"test": "test"}
        )
        print(file_doc_form._validate_file_type(file))
        
    # def test_file_doc_form_validate_file_type(self):
    #     im = Image.new(mode='RGB', size=(200, 200))
    #     im_io = BytesIO()
    #     im.save(im_io, 'JPEG')
    #     im_io.seek(0)

    #     image = InMemoryUploadedFile(
    #         im_io, None, 'random-name.jpg', 'image/jpeg', len(im_io.getvalue()), None
    #     )
    #     response = self.client.post(self.url, {'file': image})
    #     print(response)

