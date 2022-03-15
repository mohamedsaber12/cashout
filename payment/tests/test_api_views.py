# from os import stat
# from rest_framework.test import APIClient, APITestCase
# from users.tests.factories import SuperAdminUserFactory
# from django.urls import reverse
# from rest_framework import status


# class TransactionCallbackAPIView(APITestCase):

#     def setUp(self):
#         super().setUp()
#         self.client = APIClient()
#         self.user = SuperAdminUserFactory()
#         self.user.set_password("password")
#         self.user.save()

#         self.url = reverse("payment_api:trn_callback_api")
        
#     def test_url_with_get(self):
#         resp = self.client.get(self.url)
#         self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
#     def test_with_no_data(self):
#         resp = self.client.post(self.url)
#         self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        