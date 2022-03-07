# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from urllib.parse import urlencode

from users.tests.factories import (
    AdminUserFactory
)

class IncreaseBalanceRequestViewTests(TestCase):

    def setUp(self):
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.root.save()

        # self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('utilities:transfer_request'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/budget/transfer-request/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('utilities:transfer_request'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('utilities:transfer_request'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'utilities/transfer_request.html')

    def test_post_method(self):
        self.client.force_login(self.root)
        data = {
            "type": "from_accept_balance",
            "username": "Accept_username",
            "amount": 1000
        }
        response = self.client.post(
            reverse('utilities:transfer_request'),
            data
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'utilities/transfer_request.html')