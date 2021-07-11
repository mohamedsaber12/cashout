# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase, Client, RequestFactory, override_settings
from django.urls import reverse
from django.contrib.auth.models import Permission
from rest_framework_expiring_authtoken.models import ExpiringToken

from users.tests.factories import (
    SuperAdminUserFactory, AdminUserFactory, VMTDataFactory
)
from users.models import Setup, Client as ClientModel, Brand, EntitySetup
from utilities.models import Budget
from disbursement.models import Agent


class AgentsListViewTests(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('disbursement:agents_list'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.super_admin)
        response = self.client.get('/agents/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('disbursement:agents_list'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('disbursement:agents_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disbursement/agents.html')


class BalanceInquiryTests(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.brand = self.brand
        self.root.save()
        self.agent = Agent(msisdn='01021469732', wallet_provider=self.root, super=True)
        self.agent.save()
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement')
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.setup = Setup(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=True
        )
        self.setup.save()
        self.budget = Budget(disburser=self.root)
        self.budget.save()


        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse('disbursement:balance_inquiry',
            kwargs={'username':self.root.username}
        ))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get(f'/budget/inquiry/{self.root.username}/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(
            reverse('disbursement:balance_inquiry',
            kwargs={'username':self.root.username}
        ))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(
            reverse('disbursement:balance_inquiry',
            kwargs={'username':self.root.username}
        ))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disbursement/balance_inquiry.html')

    def test_post_method(self):
        self.client.force_login(self.root)

        data = {
            "pin": "123456",
        }
        response = self.client.post(
            reverse('disbursement:balance_inquiry',
                kwargs={'username':self.root.username}
            ),
            data
        )
        self.assertEqual(response.status_code, 200)


class SuperAdminAgentsSetupTests(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.brand = self.brand
        self.root.save()
        self.entity_setup = EntitySetup(
            user=self.super_admin,
            entity=self.root,
            agents_setup=True,
            fees_setup=True
        )
        self.entity_setup.save()
        # self.agent = Agent(msisdn='01021469732', wallet_provider=self.root, super=True)
        # self.agent.save()
        # self.root.user_permissions. \
        #     add(Permission.objects.get(
        #         content_type__app_label='users', codename='has_disbursement')
        # )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        # self.setup = Setup(
        #         user=self.root,
        #         levels_setup=True,
        #         maker_setup=True,
        #         checker_setup=True,
        #         category_setup=True,
        #         pin_setup=True
        # )
        # self.setup.save()
        # self.budget = Budget(disburser=self.root)
        # self.budget.save()


        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse('disbursement:add_agents',
                kwargs={'token':'token'}
            )
        )
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.super_admin)
        token, created = ExpiringToken.objects.get_or_create(user=self.root)
        if created:
            response = self.client.get(f'/client/creation/agents/{token.key}/')
            self.assertEqual(response.status_code, 200)

    # def test_view_url_accessible_by_name(self):
    #     self.client.force_login(self.root)
    #     token, created = ExpiringToken.objects.get_or_create(user=self.root)
    #     if created:
    #         response = self.client.get(
    #             reverse('disbursement:add_agents',
    #                 kwargs={'token':token.key}
    #             )
    #         )
    #         self.assertEqual(response.status_code, 200)

    # def test_view_uses_correct_template(self):
    #     self.client.force_login(self.root)
    #     token, created = ExpiringToken.objects.get_or_create(user=self.root)
    #     if created:
    #         response = self.client.get(
    #             reverse('disbursement:add_agents',
    #                 kwargs={'token':token.key}
    #             )
    #         )
    #         self.assertEqual(response.status_code, 200)
    #         self.assertTemplateUsed(response, 'entity/add_agent.html')

    # def test_post_method(self):
    #     self.client.force_login(self.root)
    #
    #     data = {
    #         "pin": "123456",
    #     }
    #     response = self.client.post(
    #             reverse('disbursement:balance_inquiry',
    #                     kwargs={'username':self.root.username}
    #                     ),
    #             data
    #     )
    #     self.assertEqual(response.status_code, 200)