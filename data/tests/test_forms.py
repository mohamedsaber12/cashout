from django.test import RequestFactory
from django.test import TestCase, RequestFactory
from users.tests.factories import SuperAdminUserFactory
from data.forms import FileDocumentForm
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile


# class MockRequest:
#     def get(self):
#         request_factory = RequestFactory()
#         return request_factory.get("/")
    
    
# class TestFileDocumentForm(TestCase):
#     def setUp(self):
#         super().setUp()
#         self.request = MockRequest()
#         self.superuser = SuperAdminUserFactory(is_superuser=True)
    
#     def test_file_doc_form_validate_file_type(self):
#         im = Image.new(mode='RGB', size=(200, 200))
#         im_io = BytesIO()
#         im.save(im_io, 'JPEG')
#         im_io.seek(0)

#         image = InMemoryUploadedFile(
#             im_io, None, 'random-name.jpg', 'image/jpeg', len(im_io.getvalue()), None
#         )
#         post_dict = {'title': 'Test Title'}
#         file_dict = {'picture': image}

#         form = FileDocumentForm(data=post_dict, files=file_dict)
#         print(form)

#         # django_friendly_file = ContentFile(image_file.read(), 'test.png')

#         # resp = form._validate_file_type(image_file)
#         # print(resp)
        
        


from rest_framework.test import APIClient, APITestCase
from users.tests.factories import SuperAdminUserFactory
from django.urls import reverse
from rest_framework import status


class TestFileDocumentForm(APITestCase):

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.user = SuperAdminUserFactory()
        self.user.set_password("password")
        self.user.save()
        self.client.login(username=self.user.username, password='password')

        self.url = reverse("data:e_wallets_home")
        
    def test_file_doc_form_validate_file_type(self):
        im = Image.new(mode='RGB', size=(200, 200))
        im_io = BytesIO()
        im.save(im_io, 'JPEG')
        im_io.seek(0)

        image = InMemoryUploadedFile(
            im_io, None, 'random-name.jpg', 'image/jpeg', len(im_io.getvalue()), None
        )
        response = self.client.post(self.url, {'file': image})
        print(response)

