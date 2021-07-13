# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase, Client, RequestFactory, override_settings
from django.urls import reverse
from django.contrib.auth.models import Permission
from rest_framework_expiring_authtoken.models import ExpiringToken

from users.tests.factories import (
    SuperAdminUserFactory, AdminUserFactory, VMTDataFactory
)
from users.models import (
    Setup, Client as ClientModel, Brand, EntitySetup, CheckerUser, Levels,
    MakerUser
)
from data.models import Doc
from utilities.models import Budget, CallWalletsModerator, FeeSetup
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
            agents_setup=False,
            fees_setup=False
        )
        self.entity_setup.save()

        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        CallWalletsModerator.objects.create(
            user_created=self.root, disbursement=False, change_profile=False, set_pin=False,
            user_inquiry=False, balance_inquiry=False
        )

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

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.super_admin)
        token, created = ExpiringToken.objects.get_or_create(user=self.root)
        if created:
            response = self.client.get(
                reverse('disbursement:add_agents',
                    kwargs={'token':token.key}
                )
            )
            self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.super_admin)
        token, created = ExpiringToken.objects.get_or_create(user=self.root)
        if created:
            response = self.client.get(
                reverse('disbursement:add_agents',
                    kwargs={'token':token.key}
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'entity/add_agent.html')

    def test_post_method(self):
        self.client.force_login(self.super_admin)
        token, created = ExpiringToken.objects.get_or_create(user=self.root)
        if created:
            data = {
                "agents-TOTAL_FORMS": 1,
                "agents-INITIAL_FORMS": 0,
                "agents-MIN_NUM_FORMS": 1,
                "agents-MAX_NUM_FORMS": 1000,
                "agents-0-id": "",
                "agents-0-msisdn": "01006332833",
                "agents-0-DELETE": "",
                "msisdn": "01021469732"
            }

            response = self.client.post(
                reverse('disbursement:add_agents',
                    kwargs={'token':token.key}
                ),
                data
            )
            self.assertRedirects(
                response,
                f'/client/fees-setup/{token.key}/'
            )


class SingleStepTransactionsViewTests(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.brand = self.brand
        self.root.set_pin('123456')
        self.root.save()
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement')
        )
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding')
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.checker_user = CheckerUser(
            id=15,
            username='test_checker_user',
            root=self.root,
            user_type=2
        )
        self.checker_user.save()
        self.level = Levels(
            max_amount_can_be_disbursed=1200,
            created=self.root
        )
        self.level.save()
        self.checker_user.level = self.level
        self.checker_user.save()
        self.checker_user.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement')
        )
        self.checker_user.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding')
        )
        self.request = RequestFactory()
        self.client = Client()
        self.budget = Budget(disburser=self.root, current_balance=150)
        self.budget.save()
        fees_setup_bank_wallet = FeeSetup(budget_related=self.budget, issuer='bc',
                                          fee_type='f', fixed_value=20)
        fees_setup_bank_wallet.save()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse(
                'disbursement:add_agents',
                kwargs={'token':'token'}
            )
        )
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/disburse/single-step/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(
            reverse('disbursement:single_step_list_create')
        )
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(
            reverse('disbursement:single_step_list_create')
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disbursement/single_step_trx_list.html')

    def test_post_method_on_vodafone(self):
        fees_setup_vodafone = FeeSetup(budget_related=self.budget, issuer='vf',
                                       fee_type='p', percentage_value=2.25)
        fees_setup_vodafone.save()
        self.client.force_login(self.checker_user)
        data = {
            "amount": 100,
            "issuer": "vodafone",
            "msisdn": '01021469732',
            "pin": "123456",
        }
        response = self.client.post(
            '%s?issuer=wallets' % (reverse('disbursement:single_step_list_create')),
            data
        )
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(
            redirect_url,
            '/disburse/single-step/'
        )

    def test_post_method_on_bank_card(self):
        self.client.force_login(self.checker_user)
        data = {
            "amount": 100,
            "issuer": "bank_card",
            "creditor_account_number": '4665543567987643',
            "creditor_name": "test test",
            "creditor_bank": "AUB",
            "transaction_type": "CASH_TRANSFER",
            "pin": "123456",
        }
        response = self.client.post(
            '%s?issuer=wallets' % (reverse('disbursement:single_step_list_create')),
            data
        )
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(
            redirect_url,
            '/disburse/single-step/'
        )

    def test_post_method_on_aman(self):
        fees_setup_aman = FeeSetup(budget_related=self.budget, issuer='am',
                                   fee_type='p', percentage_value=2.25)
        fees_setup_aman.save()
        self.client.force_login(self.checker_user)
        data = {
            "amount": 100,
            "issuer": "aman",
            "msisdn": '01021469732',
            "first_name": "test",
            "last_name": "test",
            "email": "test@p.com",
            "pin": "123456",
        }
        response = self.client.post(
            '%s?issuer=wallets' % (reverse('disbursement:single_step_list_create')),
            data
        )
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(
            redirect_url,
            '/disburse/single-step/'
        )


class DisbursementTests(TestCase):

    def Setup(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.brand = self.brand
        self.root.set_pin('123456')
        self.root.save()
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement')
        )
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding')
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.checker_user = CheckerUser(
                id=15,
                username='test_checker_user',
                root=self.root,
                user_type=2
        )
        self.checker_user.save()
        self.level = Levels(
                max_amount_can_be_disbursed=1200,
                created=self.root
        )
        self.level.save()
        self.checker_user.level = self.level
        self.checker_user.save()
        self.checker_user.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement')
        )
        self.checker_user.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding')
        )
        self.maker_user = MakerUser(
            id=14,
            username='test_maker_user',
            root=self.root,
            user_type=1
        )
        self.maker_user.save()
        self.request = RequestFactory()
        self.client = Client()
        self.budget = Budget(disburser=self.root, current_balance=150)
        self.budget.save()
        fees_setup_bank_wallet = FeeSetup(budget_related=self.budget, issuer='bc',
                                          fee_type='f', fixed_value=20)
        fees_setup_bank_wallet.save()
        fees_setup_vodafone = FeeSetup(budget_related=self.budget, issuer='vf',
                                       fee_type='p', percentage_value=2.25)
        fees_setup_vodafone.save()

        # create doc
        # self.doc = Doc.objects.create(owner=maker, disbursed_by=checker, is_disbursed=True, can_be_disbursed=True, is_processed=True, txn_id=batch_id, file_category=file_category)


    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse('disbursement:disburse',
                kwargs={'doc_id':'fake_doc_id'}
            )
        )
        self.assertRedirects(response, '/user/login/')