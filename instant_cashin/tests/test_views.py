# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import Permission

from users.tests.factories import (
    InstantAPIViewerUserFactory, AdminUserFactory
)


class InstantTransactionsListViewTests(TestCase):

    def setUp(self):
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.root.save()

        # create dashboard user
        self.dashboard_user = InstantAPIViewerUserFactory(user_type=7, root=self.root)
        self.dashboard_user.set_password('fiA#EmkjLBh9VSXy6XvFKxnR9jXt')
        self.dashboard_user.save()
        self.dashboard_user.user_permissions. \
            add(Permission.objects.get(content_type__app_label='users', codename='instant_model_onboarding'))

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('instant_cashin:wallets_trx_list'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.dashboard_user)
        response = self.client.get('/instant-cashin/instant-transactions/wallets/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.dashboard_user)
        response = self.client.get(reverse('instant_cashin:wallets_trx_list'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.dashboard_user)
        response = self.client.get(reverse('instant_cashin:wallets_trx_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'instant_cashin/instant_viewer.html')


class BankTransactionsListViewTests(TestCase):

    def setUp(self):
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.root.save()

        # create dashboard user
        self.dashboard_user = InstantAPIViewerUserFactory(user_type=7, root=self.root)
        self.dashboard_user.set_password('fiA#EmkjLBh9VSXy6XvFKxnR9jXt')
        self.dashboard_user.save()
        self.dashboard_user.user_permissions. \
            add(Permission.objects.get(content_type__app_label='users', codename='instant_model_onboarding'))

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('instant_cashin:banks_trx_list'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.dashboard_user)
        response = self.client.get('/instant-cashin/instant-transactions/banks/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.dashboard_user)
        response = self.client.get(reverse('instant_cashin:banks_trx_list'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.dashboard_user)
        response = self.client.get(reverse('instant_cashin:banks_trx_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'instant_cashin/instant_viewer.html')