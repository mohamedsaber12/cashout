# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import os
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from rest_framework_expiring_authtoken.models import ExpiringToken

from data.models import Doc, DocReview, FileCategory
from disbursement.models import (Agent, BankTransaction, DisbursementData,
                                 DisbursementDocData, PaymentLink, VMTData)
from instant_cashin.models.instant_transactions import InstantTransaction
from users.models import Brand, CheckerUser
from users.models import Client as ClientModel
from users.models import EntitySetup, Levels, MakerUser, Setup
from users.models.access_token import AccessToken
from users.models.instant_api_checker import InstantAPICheckerUser
from users.models.instant_api_viewer import InstantAPIViewerUser
from users.models.root import RootUser
from users.models.support import SupportSetup, SupportUser
from users.tests.factories import (AdminUserFactory, SuperAdminUserFactory,
                                   VMTDataFactory)
from utilities.models import (AbstractBaseDocType, Budget,
                              CallWalletsModerator, FeeSetup)


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


class BalanceInquiryMockResponse:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = True

    def json(self):
        return {
            'TXNSTATUS': '200',
            'HAS_PIN': False,
            'USER_TYPE': 'Agent',
            'BALANCE': 2000,
        }


class BalanceInquiryMockResponse_With_NotOk:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = False

    def json(self):
        return {
            'TXNSTATUS': '200',
            'HAS_PIN': False,
            'USER_TYPE': 'Agent',
            'BALANCE': 2000,
        }


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
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.setup = Setup(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=True,
        )
        self.setup.save()
        self.budget = Budget(disburser=self.root)
        self.budget.save()

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse(
                'disbursement:balance_inquiry', kwargs={'username': self.root.username}
            )
        )
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get(f'/budget/inquiry/{self.root.username}/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(
            reverse(
                'disbursement:balance_inquiry', kwargs={'username': self.root.username}
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(
            reverse(
                'disbursement:balance_inquiry', kwargs={'username': self.root.username}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disbursement/balance_inquiry.html')

    def test_post_method(self):
        self.client.force_login(self.root)

        data = {
            "pin": "123456",
        }
        response = self.client.post(
            reverse(
                'disbursement:balance_inquiry', kwargs={'username': self.root.username}
            ),
            data,
        )
        self.assertEqual(response.status_code, 200)

    def test_post_method_with_form_invalid(self):
        self.client.force_login(self.root)

        data = {
            "pin": "mjhjhj",
        }
        response = self.client.post(
            reverse(
                'disbursement:balance_inquiry', kwargs={'username': self.root.username}
            ),
            data,
        )
        self.assertEqual(response.status_code, 200)

    def test_post_method_with_superadmin(self):
        self.client.force_login(self.super_admin)

        data = {
            "pin": "123456",
        }
        response = self.client.post(
            reverse(
                'disbursement:balance_inquiry', kwargs={'username': self.root.username}
            ),
            data,
        )
        self.assertEqual(response.status_code, 200)

    @patch("requests.post", return_value=BalanceInquiryMockResponse())
    def test_post_method_with_superadmin_with_mocked_response(self, mocked):
        self.client.force_login(self.super_admin)

        data = {
            "pin": "123456",
        }
        response = self.client.post(
            reverse(
                'disbursement:balance_inquiry', kwargs={'username': self.root.username}
            ),
            data,
        )
        self.assertEqual(response.status_code, 200)

    @patch("requests.post", return_value=BalanceInquiryMockResponse_With_NotOk())
    def test_post_method_with_superadmin_with_mocked_response_with_error(self, mocked):
        self.client.force_login(self.super_admin)

        data = {
            "pin": "123456",
        }
        response = self.client.post(
            reverse(
                'disbursement:balance_inquiry', kwargs={'username': self.root.username}
            ),
            data,
        )
        self.assertEqual(response.status_code, 200)

    def test_post_method_with_exception(self):
        self.client.force_login(self.super_admin)
        vmt = VMTData.objects.get(vmt=self.super_admin)
        vmt.vmt_environment = 'test'
        vmt.save()
        data = {
            "pin": "123456",
        }
        response = self.client.post(
            reverse(
                'disbursement:balance_inquiry', kwargs={'username': self.root.username}
            ),
            data,
        )
        self.assertEqual(response.status_code, 200)


class MockResponse:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = True

    def json(self):
        return {
            "TRANSACTIONS": [
                {
                    'TXNSTATUS': '1',
                    'HAS_PIN': False,
                    'USER_TYPE': 'Agent',
                }
            ],
        }


class MockResponse_with_not_ok:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = False

    def json(self):
        return {
            "TRANSACTIONS": [
                {
                    'TXNSTATUS': '1',
                    'HAS_PIN': False,
                    'USER_TYPE': 'Agent',
                }
            ],
        }


class MockResponseWithError:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = True

    def json(self):
        return {
            "TRANSACTIONS": [
                {
                    'TXNSTATUS': '1',
                    'HAS_PIN': True,
                    'USER_TYPE': 'test',
                }
            ],
        }


class MockResponseWithoutTransactions:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = True

    def json(self):
        return {}


class MockResponseWithUSER_TYPE_Agent:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = True

    def json(self):
        return {
            "TRANSACTIONS": [
                {
                    "USER_TYPE": "false",
                    "WALLET_STATUS": "Active",
                    "USER_PROFILE": "Vodafone Agent",
                    "MSISDN": "00201020045450",
                    "MESSAGE": "inquire wallet status",
                    "HAS_PIN": False,
                }
            ]
        }


def MockValidate_Agent_Wallet():
    transactions = [
        {
            "USER_TYPE": False,
            "WALLET_STATUS": "Active",
            "USER_PROFILE": "3253256t2365t2",
            "MSISDN": "00201021469733",
            "MESSAGE": "inquire wallet status",
            "HAS_PIN": False,
        }
    ]
    return transactions, None


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
            fees_setup=False,
        )
        self.entity_setup.save()

        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        CallWalletsModerator.objects.create(
            user_created=self.root,
            disbursement=False,
            change_profile=False,
            set_pin=False,
            user_inquiry=True,
            balance_inquiry=False,
        )

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse('disbursement:add_agents', kwargs={'token': 'token'})
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
                reverse('disbursement:add_agents', kwargs={'token': token.key})
            )
            self.assertEqual(response.status_code, 200)

    def test_get_requset_EXISTING_SUPERAGENT_AGENTS(self):
        self.client_user.agents_onboarding_choice = (
            ClientModel.EXISTING_SUPERAGENT_AGENTS
        )
        self.client_user.save()
        self.client.force_login(self.super_admin)
        token, created = ExpiringToken.objects.get_or_create(user=self.root)
        if created:
            response = self.client.get(
                reverse('disbursement:add_agents', kwargs={'token': token.key})
            )
            self.assertEqual(response.status_code, 200)

    def test_get_requset_(self):
        self.client_user.agents_onboarding_choice = 3
        self.client_user.save()
        self.client.force_login(self.super_admin)
        token, created = ExpiringToken.objects.get_or_create(user=self.root)
        if created:
            response = self.client.get(
                reverse('disbursement:add_agents', kwargs={'token': token.key})
            )
            self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.super_admin)
        token, created = ExpiringToken.objects.get_or_create(user=self.root)
        if created:
            response = self.client.get(
                reverse('disbursement:add_agents', kwargs={'token': token.key})
            )
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'entity/add_agent.html')

    @patch("requests.post", return_value=MockResponseWithError())
    def test_post_method_default(self, mocked):
        # self.root.callwallets_moderator.user_inquiry=True
        # self.root.save()
        # self.client_user.agents_onboarding_choice=ClientModel.EXISTING_SUPERAGENT_AGENTS
        # self.client_user.save()
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
                "msisdn": "01021469732",
            }

            response = self.client.post(
                reverse('disbursement:add_agents', kwargs={'token': token.key}), data
            )
        self.assertEqual(response.status_code, 200)

    @patch(
        "disbursement.views.SuperAdminAgentsSetup.validate_agent_wallet",
        return_value=MockValidate_Agent_Wallet(),
    )
    def test_post_method_with_ClientModel_P2M_(self, mocked):
        self.super_agent = Agent(
            msisdn='01021469732', wallet_provider=self.root, super=True
        )
        self.super_agent.save()
        self.agent = Agent(msisdn='01021469732', wallet_provider=self.root)
        self.agent.save()
        self.client_user.agents_onboarding_choice = ClientModel.P2M
        self.client_user.save()
        self.client.force_login(self.super_admin)
        token, created = ExpiringToken.objects.get_or_create(user=self.root)
        if created:
            data = {
                "agents-TOTAL_FORMS": 1,
                "agents-INITIAL_FORMS": 0,
                "agents-MIN_NUM_FORMS": 1,
                "agents-MAX_NUM_FORMS": 1000,
                "agents-0-id": "",
                "agents-0-msisdn": "01021469733",
                "agents-0-DELETE": "",
                "msisdn": "01021469733",
            }

            response = self.client.post(
                reverse('disbursement:add_agents', kwargs={'token': token.key}), data
            )
            self.assertEqual(response.status_code, 200)

    @patch("requests.post", return_value=MockResponseWithError())
    def test_post_method_with_ClientModel_P2M_Without_transactions(self, mocked):
        self.super_agent = Agent(
            msisdn='01021469732', wallet_provider=self.root, super=True
        )
        self.super_agent.save()
        self.agent = Agent(msisdn='01021469732', wallet_provider=self.root)
        self.agent.save()
        self.client_user.agents_onboarding_choice = ClientModel.P2M
        self.client_user.save()
        self.client.force_login(self.super_admin)
        token, created = ExpiringToken.objects.get_or_create(user=self.root)
        if created:
            data = {
                "agents-TOTAL_FORMS": 1,
                "agents-INITIAL_FORMS": 0,
                "agents-MIN_NUM_FORMS": 1,
                "agents-MAX_NUM_FORMS": 1000,
                "agents-0-id": "",
                "agents-0-msisdn": "01021469733",
                "agents-0-DELETE": "",
                "msisdn": "01021469733",
            }

            response = self.client.post(
                reverse('disbursement:add_agents', kwargs={'token': token.key}), data
            )
            self.assertEqual(response.status_code, 200)

    @patch(
        "disbursement.views.SuperAdminAgentsSetup.validate_agent_wallet",
        return_value=MockValidate_Agent_Wallet(),
    )
    def test_post_method_with_ClientModel_NEW_SUPERAGENT_AGENTS(self, mocked):
        self.super_agent = Agent(
            msisdn='01021469732', wallet_provider=self.root, super=True
        )
        self.super_agent.save()
        self.agent = Agent(msisdn='01021469732', wallet_provider=self.root)
        self.agent.save()
        self.client_user.agents_onboarding_choice = ClientModel.NEW_SUPERAGENT_AGENTS
        self.client_user.save()
        self.client.force_login(self.super_admin)
        token, created = ExpiringToken.objects.get_or_create(user=self.root)
        if created:
            data = {
                "agents-TOTAL_FORMS": 1,
                "agents-INITIAL_FORMS": 0,
                "agents-MIN_NUM_FORMS": 1,
                "agents-MAX_NUM_FORMS": 1000,
                "agents-0-id": "",
                "agents-0-msisdn": "01021469733",
                "agents-0-DELETE": "",
                "msisdn": "01021469733",
            }

            response = self.client.post(
                reverse('disbursement:add_agents', kwargs={'token': token.key}), data
            )
            self.assertEqual(response.status_code, 200)

    @patch(
        "disbursement.views.SuperAdminAgentsSetup.validate_agent_wallet",
        return_value=MockValidate_Agent_Wallet(),
    )
    def test_post_method_with_ClientModel_EXISTING_SUPERAGENT_NEW_AGENTS(self, mocked):
        self.super_agent = Agent(
            msisdn='01021469732', wallet_provider=self.root, super=True
        )
        self.super_agent.save()
        self.agent = Agent(msisdn='01021469732', wallet_provider=self.root)
        self.agent.save()
        self.client_user.agents_onboarding_choice = (
            ClientModel.EXISTING_SUPERAGENT_NEW_AGENTS
        )
        self.client_user.save()
        self.client.force_login(self.super_admin)
        token, created = ExpiringToken.objects.get_or_create(user=self.root)
        if created:
            data = {
                "agents-TOTAL_FORMS": 1,
                "agents-INITIAL_FORMS": 0,
                "agents-MIN_NUM_FORMS": 1,
                "agents-MAX_NUM_FORMS": 1000,
                "agents-0-id": "",
                "agents-0-msisdn": "01021469733",
                "agents-0-DELETE": "",
                "msisdn": "01021469733",
            }

            response = self.client.post(
                reverse('disbursement:add_agents', kwargs={'token': token.key}), data
            )
            self.assertEqual(response.status_code, 200)

    @patch("requests.post", return_value=MockResponseWithoutTransactions())
    def test_post_method_with_ClientModel_EXISTING_SUPERAGENT_NEW_AGENTS_without_transaction(
        self, mocked
    ):
        self.super_agent = Agent(
            msisdn='01021469732', wallet_provider=self.root, super=True
        )
        self.super_agent.save()
        self.agent = Agent(msisdn='01021469732', wallet_provider=self.root)
        self.agent.save()
        self.client_user.agents_onboarding_choice = ClientModel.NEW_SUPERAGENT_AGENTS
        self.client_user.save()
        self.client.force_login(self.super_admin)
        token, created = ExpiringToken.objects.get_or_create(user=self.root)
        if created:
            data = {
                "agents-TOTAL_FORMS": 1,
                "agents-INITIAL_FORMS": 0,
                "agents-MIN_NUM_FORMS": 1,
                "agents-MAX_NUM_FORMS": 1000,
                "agents-0-id": "",
                "agents-0-msisdn": "01021469733",
                "agents-0-DELETE": "",
                "msisdn": "01021469733",
            }

            response = self.client.post(
                reverse('disbursement:add_agents', kwargs={'token': token.key}), data
            )
            self.assertEqual(response.status_code, 200)

    @patch("requests.post", return_value=MockResponseWithUSER_TYPE_Agent())
    def test_post_method_with_ClientModel_EXISTING_SUPERAGENT_NEW_AGENTS_with_user_type_false(
        self, mocked
    ):
        self.super_agent = Agent(
            msisdn='01021469732', wallet_provider=self.root, super=True
        )
        self.super_agent.save()
        self.agent = Agent(msisdn='01021469732', wallet_provider=self.root)
        self.agent.save()
        self.client_user.agents_onboarding_choice = ClientModel.NEW_SUPERAGENT_AGENTS
        self.client_user.save()
        self.client.force_login(self.super_admin)
        token, created = ExpiringToken.objects.get_or_create(user=self.root)
        if created:
            data = {
                "agents-TOTAL_FORMS": 1,
                "agents-INITIAL_FORMS": 0,
                "agents-MIN_NUM_FORMS": 1,
                "agents-MAX_NUM_FORMS": 1000,
                "agents-0-id": "",
                "agents-0-msisdn": "01021469733",
                "agents-0-DELETE": "",
                "msisdn": "01021469733",
            }

            response = self.client.post(
                reverse('disbursement:add_agents', kwargs={'token': token.key}), data
            )
            self.assertEqual(response.status_code, 200)

    # @patch("requests.post", return_value=MockResponseWithUSER_TYPE_Agent())
    def test_post_method_with_ClientModel_With_exception(self):
        self.super_agent = Agent(
            msisdn='01021469732', wallet_provider=self.root, super=True
        )
        self.super_agent.save()
        self.vmt_data_obj.vmt_environment = "test"
        self.vmt_data_obj.save()
        self.agent = Agent(msisdn='01021469732', wallet_provider=self.root)
        self.agent.save()
        self.client_user.agents_onboarding_choice = ClientModel.NEW_SUPERAGENT_AGENTS
        self.client_user.save()
        self.client.force_login(self.super_admin)
        token, created = ExpiringToken.objects.get_or_create(user=self.root)
        if created:
            data = {
                "agents-TOTAL_FORMS": 1,
                "agents-INITIAL_FORMS": 0,
                "agents-MIN_NUM_FORMS": 1,
                "agents-MAX_NUM_FORMS": 1000,
                "agents-0-id": "",
                "agents-0-msisdn": "01021469733",
                "agents-0-DELETE": "",
                "msisdn": "01021469733",
            }

            response = self.client.post(
                reverse('disbursement:add_agents', kwargs={'token': token.key}), data
            )
            self.assertEqual(response.status_code, 200)

    @patch("requests.post", return_value=MockResponse_with_not_ok())
    def test_post_method_with_ClientModel_With_not_ok(self, mocked):
        self.super_agent = Agent(
            msisdn='01021469732', wallet_provider=self.root, super=True
        )
        self.super_agent.save()
        self.vmt_data_obj.vmt_environment = "test"
        self.vmt_data_obj.save()
        self.agent = Agent(msisdn='01021469732', wallet_provider=self.root)
        self.agent.save()
        self.client_user.agents_onboarding_choice = (
            ClientModel.EXISTING_SUPERAGENT_AGENTS
        )
        self.client_user.save()
        self.client.force_login(self.super_admin)
        token, created = ExpiringToken.objects.get_or_create(user=self.root)
        if created:
            data = {
                "agents-TOTAL_FORMS": 1,
                "agents-INITIAL_FORMS": 0,
                "agents-MIN_NUM_FORMS": 1,
                "agents-MAX_NUM_FORMS": 1000,
                "agents-0-id": "",
                "agents-0-msisdn": "01021469733",
                "agents-0-DELETE": "",
                "msisdn": "01021469733",
            }

            response = self.client.post(
                reverse('disbursement:add_agents', kwargs={'token': token.key}), data
            )
            self.assertEqual(response.status_code, 200)

    @patch("requests.post", return_value=MockResponse())
    def test_post_method(self, mocked):
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
                "msisdn": "01021469732",
            }

            response = self.client.post(
                reverse('disbursement:add_agents', kwargs={'token': token.key}), data
            )
            self.assertRedirects(response, f'/client/fees-setup/{token.key}/')

    @patch("requests.post", return_value=MockResponseWithError())
    def test_post_method_EXISTING_SUPERAGENT_AGENTS(self, mocked):

        self.client_user.agents_onboarding_choice = (
            ClientModel.EXISTING_SUPERAGENT_AGENTS
        )
        self.client_user.save()
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
                "msisdn": "01021469732",
            }

            response = self.client.post(
                reverse('disbursement:add_agents', kwargs={'token': token.key}), data
            )
        self.assertEqual(response.status_code, 200)


class SingleStepTransactionMockResponse_failed:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = True

    def json(self):
        return {
            'TXNSTATUS': '200',
            'disbursement_status': 'failed',
            'success': 'success',
        }


class SingleStepTransactionMockResponse_Successful:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = True

    def json(self):
        return {'TXNSTATUS': '200', 'disbursement_status': 'Successful'}


class SingleStepTransactionMockResponse_failed:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = True

    def json(self):
        return {'TXNSTATUS': '200', 'disbursement_status': 'failed'}


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
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.setup = Setup(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=True,
        )
        self.setup.save()
        self.checker_user = CheckerUser(
            id=15, username='test_checker_user', root=self.root, user_type=2
        )
        self.checker_user.save()
        self.level = Levels(max_amount_can_be_disbursed=1200, created=self.root)
        self.level.save()
        self.checker_user.level = self.level
        self.checker_user.save()
        self.checker_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.checker_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.request = RequestFactory()
        self.client = Client()
        self.budget = Budget(disburser=self.root, current_balance=150)
        self.budget.save()
        fees_setup_bank_wallet = FeeSetup(
            budget_related=self.budget, issuer='bc', fee_type='f', fixed_value=20
        )
        fees_setup_bank_wallet.save()

        self.support_user = SupportUser.objects.create(
            username="support_user1",
            email="support_user1@gmail.com",
            user_type=8,
            id=151,
        )
        self.support_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.support_user_setup = SupportSetup.objects.create(
            support_user=self.support_user, user_created=self.super_admin
        )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse('disbursement:add_agents', kwargs={'token': 'token'})
        )
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/disburse/single-step/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.support_user)
        response = self.client.get(
            '%s?admin_hierarchy=1&issuer=wallets'
            % (reverse('disbursement:single_step_list_create'))
        )
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('disbursement:single_step_list_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disbursement/single_step_trx_list.html')

    def test_post_method_on_vodafone(self):
        fees_setup_vodafone = FeeSetup(
            budget_related=self.budget, issuer='vf', fee_type='p', percentage_value=2.25
        )
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
            data,
        )
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/disburse/single-step/')

    def test_post_method_on_vodafone_using_user_from_accept(self):
        self.root.from_accept = True
        self.root.save()
        fees_setup_vodafone = FeeSetup(
            budget_related=self.budget, issuer='vf', fee_type='p', percentage_value=2.25
        )
        fees_setup_vodafone.save()
        self.client.force_login(self.root)
        data = {
            "amount": 100,
            "issuer": "vodafone",
            "msisdn": '01021469732',
            "pin": "123456",
            "transaction_type": "CASH_TRANSFER",
        }
        response = self.client.post(
            '%s?issuer=wallets' % (reverse('disbursement:single_step_list_create')),
            data,
        )
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/disburse/single-step/')

    @patch("requests.post", return_value=SingleStepTransactionMockResponse_failed())
    def test_post_method_on_vodafone_using_user_from_accept_with_failed_request(
        self, mocked
    ):
        self.root.from_accept = True
        self.root.save()
        fees_setup_vodafone = FeeSetup(
            budget_related=self.budget, issuer='vf', fee_type='p', percentage_value=2.25
        )
        fees_setup_vodafone.save()
        self.client.force_login(self.root)
        data = {
            "amount": 100,
            "issuer": "vodafone",
            "msisdn": '01021469732',
            "pin": "123456",
            "transaction_type": "CASH_TRANSFER",
        }
        response = self.client.post(
            '%s?issuer=wallets' % (reverse('disbursement:single_step_list_create')),
            data,
        )
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/disburse/single-step/')

    @patch("requests.post", return_value=SingleStepTransactionMockResponse_Successful())
    def test_post_method_on_vodafone_using_user_from_accept_with_successful_request(
        self, mocked
    ):
        self.root.from_accept = True
        self.root.save()
        fees_setup_vodafone = FeeSetup(
            budget_related=self.budget, issuer='vf', fee_type='p', percentage_value=2.25
        )
        fees_setup_vodafone.save()
        self.client.force_login(self.root)
        data = {
            "amount": 100,
            "issuer": "vodafone",
            "msisdn": '01021469732',
            "pin": "123456",
            "transaction_type": "CASH_TRANSFER",
        }
        response = self.client.post(
            '%s?issuer=wallets' % (reverse('disbursement:single_step_list_create')),
            data,
        )
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/disburse/single-step/')

    @patch("requests.post", return_value=SingleStepTransactionMockResponse_Successful())
    def test_post_method_on_vodafone_using_user_from_accept_and_allowed_to_be_bulk_with_successful_request(
        self, mocked
    ):
        self.root.from_accept = True
        self.root.allowed_to_be_bulk = True
        self.root.save()
        fees_setup_vodafone = FeeSetup(
            budget_related=self.budget, issuer='vf', fee_type='p', percentage_value=2.25
        )
        fees_setup_vodafone.save()
        self.client.force_login(self.root)
        data = {
            "amount": 100,
            "issuer": "vodafone",
            "msisdn": '01021469732',
            "pin": "123456",
            "transaction_type": "CASH_TRANSFER",
        }
        response = self.client.post(
            '%s?issuer=wallets' % (reverse('disbursement:single_step_list_create')),
            data,
        )
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/disburse/single-step/')

    @patch("requests.post", return_value=SingleStepTransactionMockResponse_failed())
    def test_post_method_on_bank_card_with_mock(self, mocked):
        self.client.force_login(self.checker_user)
        os.environ.setdefault('DECLINE_SINGLE_STEP_URL', 'DECLINE_SINGLE_STEP_URL')
        os.environ.setdefault('SINGLE_STEP_TOKEN', 'SINGLE_STEP_TOKEN')
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
            data,
        )
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/disburse/single-step/')

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
            data,
        )
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/disburse/single-step/')

    def test_post_method_on_aman(self):
        fees_setup_aman = FeeSetup(
            budget_related=self.budget, issuer='am', fee_type='p', percentage_value=2.25
        )
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
            data,
        )
        self.assertEqual(str(response.url).split('?')[0], '/disburse/single-step/')

    def test_post_method_on_bank_wallet(self):
        fees_setup_aman = FeeSetup(
            budget_related=self.budget, issuer='am', fee_type='p', percentage_value=2.25
        )
        fees_setup_aman.save()
        self.client.force_login(self.checker_user)
        data = {
            "amount": 100,
            "issuer": "bank_wallet",
            "msisdn": '01021469732',
            "full_name": "test",
            "pin": "123456",
        }
        response = self.client.post(
            '%s?issuer=wallets' % (reverse('disbursement:single_step_list_create')),
            data,
        )
        self.assertEqual(str(response.url).split('?')[0], '/disburse/single-step/')

    def test_post_method_on_Invalid(self):
        fees_setup_aman = FeeSetup(
            budget_related=self.budget, issuer='am', fee_type='p', percentage_value=2.25
        )
        fees_setup_aman.save()
        self.client.force_login(self.checker_user)
        data = {
            "amount": 100,
            "issuer": "aman",
            "msisdn": '01021469732',
            "last_name": "test",
            "email": "test@p.com",
            "pin": "123456",
        }
        response = self.client.post(
            '%s?issuer=wallets' % (reverse('disbursement:single_step_list_create')),
            data,
        )


class DisbursementMockResponse:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = True

    def json(self):
        return {'TXNSTATUS': '200'}


class DisbursementMockResponse_WithError:
    def __init__(self):
        self.status_code = 400
        self.text = 'test'
        self.ok = False

    def json(self):
        return {'TXNSTATUS': '400'}


class DisbursementMockResponse_WithStatus300:
    def __init__(self):
        self.status_code = 300
        self.text = 'test'
        self.ok = False

    def json(self):
        return {'TXNSTATUS': '400'}


class DisbursementTests(TestCase):
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
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.checker_user = CheckerUser(
            hierarchy=1,
            id=15,
            username='test_checker_user',
            root=self.root,
            user_type=2,
        )
        self.checker_user.save()
        self.level = Levels(max_amount_can_be_disbursed=1200, created=self.root)
        self.level.save()
        self.checker_user.level = self.level
        self.checker_user.save()
        self.checker_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.checker_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.maker_user = MakerUser(
            hierarchy=1,
            id=14,
            username='test_maker_user',
            email='t@mk.com',
            root=self.root,
            user_type=1,
        )
        self.maker_user.save()
        self.budget = Budget(disburser=self.root, current_balance=150)
        self.budget.save()
        fees_setup_bank_wallet = FeeSetup(
            budget_related=self.budget, issuer='bc', fee_type='f', fixed_value=20
        )
        fees_setup_bank_wallet.save()
        fees_setup_vodafone = FeeSetup(
            budget_related=self.budget, issuer='vf', fee_type='p', percentage_value=2.25
        )
        fees_setup_vodafone.save()

        # create doc, doc_review, DisbursementDocData, file category
        file_category = FileCategory.objects.create(
            user_created=self.root, no_of_reviews_required=1
        )
        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=file_category,
            is_disbursed=False,
            can_be_disbursed=True,
            is_processed=True,
        )
        doc_review = DocReview.objects.create(
            is_ok=True,
            doc=self.doc,
            user_created=self.checker_user,
        )
        disb_data_doc = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse('disbursement:disburse', kwargs={'doc_id': 'fake_doc_id'})
        )
        self.assertRedirects(response, '/user/login/')

    def test_disburse_document_with_get_method(self):
        self.client.force_login(self.checker_user)
        response = self.client.get(
            reverse('disbursement:disburse', kwargs={'doc_id': self.doc.id})
        )
        self.assertEqual(str(response.url).split('?')[0], f'/documents/{self.doc.id}/')

    def test_disburse_document(self):
        self.client.force_login(self.checker_user)
        response = self.client.post(
            reverse('disbursement:disburse', kwargs={'doc_id': self.doc.id}),
            {'pin': '123456'},
        )
        self.assertEqual(str(response.url).split('?')[0], f'/documents/{self.doc.id}/')

    @patch("requests.post", return_value=DisbursementMockResponse())
    def test_disburse_document_successful_mock(self, mocked):
        self.client.force_login(self.checker_user)
        self.checker_user.hierarchy = self.maker_user.hierarchy
        self.checker_user.save()
        response = self.client.post(
            reverse('disbursement:disburse', kwargs={'doc_id': self.doc.id}),
            {'pin': '123456'},
        )
        self.assertEqual(str(response.url).split('?')[0], f'/documents/{self.doc.id}/')

    @patch("requests.post", return_value=DisbursementMockResponse())
    def test_disburse_document_using_user_hierarchy_not_equal_owner_hierarchy(
        self, mocked
    ):
        self.client.force_login(self.checker_user)
        self.checker_user.hierarchy = 2
        self.checker_user.save()
        response = self.client.post(
            reverse('disbursement:disburse', kwargs={'doc_id': self.doc.id}),
            {'pin': '123456'},
        )
        self.assertEqual(str(response.url).split('?')[0], f'/documents/{self.doc.id}/')

    @patch("requests.post", return_value=DisbursementMockResponse_WithError())
    def test_disburse_document_failed_mock(self, mocked):
        self.client.force_login(self.checker_user)
        response = self.client.post(
            reverse('disbursement:disburse', kwargs={'doc_id': self.doc.id}),
            {'pin': '123456'},
        )
        self.assertEqual(str(response.url).split('?')[0], f'/documents/{self.doc.id}/')

    @patch("requests.post", return_value=DisbursementMockResponse_WithStatus300())
    def test_disburse_document_failed_mock_status_300(self, mocked):
        self.client.force_login(self.checker_user)
        response = self.client.post(
            reverse('disbursement:disburse', kwargs={'doc_id': self.doc.id}),
            {'pin': '123456'},
        )
        self.assertEqual(str(response.url).split('?')[0], f'/documents/{self.doc.id}/')


class DownloadSampleSheetViewTests(TestCase):
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
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            '%s?type=e_wallets' % reverse('disbursement:export_sample_file')
        )
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/disburse/export-sample-file/?type=e_wallets')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name_for_e_wallets_sheets(self):
        self.client.force_login(self.root)
        response = self.client.get(
            '%s?type=e_wallets' % reverse('disbursement:export_sample_file')
        )
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name_for_bank_wallet_sheets(self):
        self.client.force_login(self.root)
        response = self.client.get(
            '%s?type=bank_wallets' % reverse('disbursement:export_sample_file')
        )
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name_for_bank_card_sheets(self):
        self.client.force_login(self.root)
        response = self.client.get(
            '%s?type=bank_cards' % reverse('disbursement:export_sample_file')
        )
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name_for_other_sheets(self):
        self.client.force_login(self.root)
        response = self.client.get(
            '%s?type=test' % reverse('disbursement:export_sample_file')
        )
        self.assertEqual(response.status_code, 404)


class DisbursementDocTransactionsViewTests(TestCase):
    def setUp(self):
        self.super_admin = SuperAdminUserFactory(id=111)
        self.super_admin.save()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.brand = self.brand
        self.root.set_pin('123456')
        self.root.save()
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.setup = Setup.objects.create(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=True,
        )
        self.entity_setup = EntitySetup.objects.create(
            user=self.super_admin, entity=self.root, agents_setup=True, fees_setup=True
        )
        self.checker_user = CheckerUser(
            id=15, username='test_checker_user', root=self.root, user_type=2
        )
        self.checker_user.save()
        self.level = Levels(max_amount_can_be_disbursed=1200, created=self.root)
        self.level.save()
        self.checker_user.level = self.level
        self.checker_user.save()
        self.checker_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.checker_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.maker_user = MakerUser(
            id=14,
            username='test_maker_user',
            email='t@mk.com',
            root=self.root,
            user_type=1,
        )
        self.maker_user.save()
        self.budget = Budget(disburser=self.root, current_balance=150)
        self.budget.save()
        fees_setup_bank_wallet = FeeSetup(
            budget_related=self.budget, issuer='bc', fee_type='f', fixed_value=20
        )
        fees_setup_bank_wallet.save()
        fees_setup_vodafone = FeeSetup(
            budget_related=self.budget, issuer='vf', fee_type='p', percentage_value=2.25
        )
        fees_setup_vodafone.save()

        # create doc, doc_review, DisbursementDocData, file category
        file_category = FileCategory.objects.create(user_created=self.root)
        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
        )
        doc_review = DocReview.objects.create(
            is_ok=True,
            doc=self.doc,
            user_created=self.checker_user,
        )
        disb_data_doc = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse('disbursement:disbursed_data', kwargs={'doc_id': self.doc.id})
        )
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get(f'/disburse/report/{self.doc.id}/')
        self.assertEqual(response.status_code, 200)

    def test_forbidden_sheet_transactions_view(self):
        self.client.force_login(self.root)
        self.doc.is_disbursed = False
        self.doc.save()
        response = self.client.get(
            reverse('disbursement:disbursed_data', kwargs={'doc_id': self.doc.id})
        )
        self.assertEqual(response.status_code, 401)

    def test_e_wallets_sheet_transactions_view(self):
        self.client.force_login(self.root)
        response = self.client.get(
            reverse('disbursement:disbursed_data', kwargs={'doc_id': self.doc.id})
        )
        self.assertEqual(response.status_code, 200)

    def test_sheet_transactions_view_with_ajax_export_failed(self):
        self.client.force_login(self.root)
        response = self.client.get(
            '%s?export_failed=true'
            % (reverse('disbursement:disbursed_data', kwargs={'doc_id': self.doc.id})),
            {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)

    def test_sheet_transactions_view_with_ajax_export_success(self):
        self.client.force_login(self.root)
        response = self.client.get(
            '%s?export_success=true'
            % (reverse('disbursement:disbursed_data', kwargs={'doc_id': self.doc.id})),
            {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)

    def test_sheet_transactions_view_with_ajax_export_all(self):
        self.client.force_login(self.root)
        response = self.client.get(
            '%s?export_all=true'
            % (reverse('disbursement:disbursed_data', kwargs={'doc_id': self.doc.id})),
            {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)

    def test_sheet_transactions_view_with_ajax_with_search(self):
        self.client.force_login(self.root)
        response = self.client.get(
            '%s?search=test'
            % (reverse('disbursement:disbursed_data', kwargs={'doc_id': self.doc.id})),
            {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)

    def test_bank_wallets_sheet_transactions_view(self):
        self.client.force_login(self.root)
        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()
        self.instanttransaction1 = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.AMAN,
            disbursed_date=datetime.datetime.now(),
            status='d',
        )
        self.instanttransaction2 = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.AMAN,
            disbursed_date=datetime.datetime.now(),
            status='P',
        )

        response = self.client.get(
            '%s?search=test'
            % (reverse('disbursement:disbursed_data', kwargs={'doc_id': self.doc.id}))
        )
        self.assertEqual(response.status_code, 200)

    def test_bank_wallets_sheet_transactions_view_with_pending_transaction(self):
        self.client.force_login(self.root)
        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()
        self.instanttransaction1 = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.AMAN,
            disbursed_date=datetime.datetime.now(),
            status='d',
        )
        self.instanttransaction2 = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.AMAN,
            disbursed_date=datetime.datetime.now(),
            status='F',
        )
        self.instanttransaction2 = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.AMAN,
            disbursed_date=datetime.datetime.now(),
            status='R',
        )
        self.instanttransaction3 = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.AMAN,
            disbursed_date=datetime.datetime.now(),
            status='J',
        )

        response = self.client.get(
            '%s?search=test'
            % (reverse('disbursement:disbursed_data', kwargs={'doc_id': self.doc.id}))
        )
        self.assertEqual(response.status_code, 200)

    def test_bank_cards_sheet_transactions_view(self):
        self.client.force_login(self.root)
        self.doc.type_of = AbstractBaseDocType.BANK_CARDS
        self.doc.save()
        response = self.client.get(
            '%s?search=test'
            % (reverse('disbursement:disbursed_data', kwargs={'doc_id': self.doc.id}))
        )
        self.assertEqual(response.status_code, 200)


class FailedDisbursedForDownloadTests(TestCase):
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
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.setup = Setup.objects.create(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=True,
        )
        self.entity_setup = EntitySetup.objects.create(
            user=self.super_admin, entity=self.root, agents_setup=True, fees_setup=True
        )
        self.checker_user = CheckerUser(
            id=15, username='test_checker_user', root=self.root, user_type=2
        )
        self.checker_user.save()
        self.level = Levels(max_amount_can_be_disbursed=1200, created=self.root)
        self.level.save()
        self.checker_user.level = self.level
        self.checker_user.save()
        self.checker_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.checker_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.maker_user = MakerUser(
            id=14,
            username='test_maker_user',
            email='t@mk.com',
            root=self.root,
            user_type=1,
        )
        self.maker_user.save()
        self.budget = Budget(disburser=self.root, current_balance=150)
        self.budget.save()
        fees_setup_bank_wallet = FeeSetup(
            budget_related=self.budget, issuer='bc', fee_type='f', fixed_value=20
        )
        fees_setup_bank_wallet.save()
        fees_setup_vodafone = FeeSetup(
            budget_related=self.budget, issuer='vf', fee_type='p', percentage_value=2.25
        )
        fees_setup_vodafone.save()

        # create doc, doc_review, DisbursementDocData, file category
        file_category = FileCategory.objects.create(user_created=self.root)
        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
        )
        doc_review = DocReview.objects.create(
            is_ok=True,
            doc=self.doc,
            user_created=self.checker_user,
        )
        disb_data_doc = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse('disbursement:download_failed', kwargs={'doc_id': self.doc.id})
        )
        self.assertRedirects(response, '/user/login/')

    def test_forbidden_download(self):
        self.client.force_login(self.root)
        self.doc.is_disbursed = False
        self.doc.save()
        response = self.client.get(
            reverse('disbursement:download_failed', kwargs={'doc_id': self.doc.id})
        )
        self.assertEqual(response.status_code, 401)

    def test_file_not_exist(self):
        self.client.force_login(self.root)
        response = self.client.get(
            f'/disburse/export_failed_download/{self.doc.id}/?filename=test'
        )
        self.assertEqual(response.status_code, 404)

    def test_file_without_filename(self):
        self.client.force_login(self.root)
        response = self.client.get(f'/disburse/export_failed_download/{self.doc.id}/')
        self.assertEqual(response.status_code, 404)

    def test_file_exist(self):
        with open('/app/mediafiles/media/documents/disbursement/test.txt', 'w') as fp:
            pass
        self.client.force_login(self.root)
        response = self.client.get(
            f'/disburse/export_failed_download/{self.doc.id}/?filename=test.txt'
        )
        self.assertEqual(response.status_code, 200)


class ExportClientsTransactionsReportPerSuperAdminTests(TestCase):
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
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.setup = Setup.objects.create(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=True,
        )
        self.entity_setup = EntitySetup.objects.create(
            user=self.super_admin, entity=self.root, agents_setup=True, fees_setup=True
        )
        self.checker_user = CheckerUser(
            id=15, username='test_checker_user', root=self.root, user_type=2
        )
        self.checker_user.save()
        self.level = Levels(max_amount_can_be_disbursed=1200, created=self.root)
        self.level.save()
        self.checker_user.level = self.level
        self.checker_user.save()
        self.checker_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.checker_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.maker_user = MakerUser(
            id=14,
            username='test_maker_user',
            email='t@mk.com',
            root=self.root,
            user_type=1,
        )
        self.maker_user.save()
        self.budget = Budget(disburser=self.root, current_balance=150)
        self.budget.save()
        fees_setup_bank_wallet = FeeSetup(
            budget_related=self.budget, issuer='bc', fee_type='f', fixed_value=20
        )
        fees_setup_bank_wallet.save()
        fees_setup_vodafone = FeeSetup(
            budget_related=self.budget, issuer='vf', fee_type='p', percentage_value=2.25
        )
        fees_setup_vodafone.save()

        # create doc, doc_review, DisbursementDocData, file category
        file_category = FileCategory.objects.create(user_created=self.root)
        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
        )
        doc_review = DocReview.objects.create(
            is_ok=True,
            doc=self.doc,
            user_created=self.checker_user,
        )
        disb_data_doc = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse('disbursement:export_clients_transactions_report')
        )
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.super_admin)
        response = self.client.get('/disburse/export-clients-transactions-report/')
        self.assertEqual(response.status_code, 401)

    def test_request_with_ajax_with_status_all(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(
            '/disburse/export-clients-transactions-report/?'
            + 'start_date=2000-01-01&end_date=2021-01-01&status=all',
            {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)

    def test_request_with_ajax_with_status_success(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(
            '/disburse/export-clients-transactions-report/?'
            + 'start_date=2000-01-01&end_date=2021-01-01&status=success',
            {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)

    def test_request_with_ajax_with_status_failed(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(
            '/disburse/export-clients-transactions-report/?'
            + 'start_date=2000-01-01&end_date=2021-01-01&status=failed',
            {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)

    def test_request_with_ajax_with_status_pending(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(
            '/disburse/export-clients-transactions-report/?'
            + 'start_date=2000-01-01&end_date=2021-01-01&status=pending',
            {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 401)


class DownloadFailedValidationFileTests(TestCase):
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
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.setup = Setup.objects.create(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=True,
        )
        self.entity_setup = EntitySetup.objects.create(
            user=self.super_admin, entity=self.root, agents_setup=True, fees_setup=True
        )
        self.checker_user = CheckerUser(
            id=15, username='test_checker_user', root=self.root, user_type=2
        )
        self.checker_user.save()
        self.level = Levels(max_amount_can_be_disbursed=1200, created=self.root)
        self.level.save()
        self.checker_user.level = self.level
        self.checker_user.save()
        self.checker_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.checker_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.maker_user = MakerUser(
            id=14,
            username='test_maker_user',
            email='t@mk.com',
            root=self.root,
            user_type=1,
        )
        self.maker_user.save()
        self.budget = Budget(disburser=self.root, current_balance=150)
        self.budget.save()
        fees_setup_bank_wallet = FeeSetup(
            budget_related=self.budget, issuer='bc', fee_type='f', fixed_value=20
        )
        fees_setup_bank_wallet.save()
        fees_setup_vodafone = FeeSetup(
            budget_related=self.budget, issuer='vf', fee_type='p', percentage_value=2.25
        )
        fees_setup_vodafone.save()

        # create doc, doc_review, DisbursementDocData, file category
        file_category = FileCategory.objects.create(user_created=self.root)
        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
        )
        doc_review = DocReview.objects.create(
            is_ok=True,
            doc=self.doc,
            user_created=self.checker_user,
        )
        disb_data_doc = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse(
                'disbursement:download_validation_failed',
                kwargs={'doc_id': self.doc.id},
            )
        )
        self.assertRedirects(response, '/user/login/')

    def test_forbidden_download(self):
        self.client.force_login(self.root)
        self.doc.is_disbursed = False
        self.doc.save()
        response = self.client.get(
            reverse(
                'disbursement:download_validation_failed',
                kwargs={'doc_id': self.doc.id},
            )
        )
        self.assertEqual(response.status_code, 401)

    def test_file_not_exist(self):
        self.client.force_login(self.maker_user)
        response = self.client.get(
            f'/disburse/export_failed_validation_download/{self.doc.id}/?filename=test'
        )
        self.assertEqual(response.status_code, 404)

    def test_file_without_filename(self):
        self.client.force_login(self.maker_user)
        response = self.client.get(
            f'/disburse/export_failed_validation_download/{self.doc.id}/'
        )
        self.assertEqual(response.status_code, 404)

    def test_file_exist(self):
        with open('/app/mediafiles/media/documents/disbursement/test.txt', 'w') as fp:
            pass
        self.client.force_login(self.maker_user)
        response = self.client.get(
            f'/disburse/export_failed_validation_download/{self.doc.id}/?filename=test.txt'
        )
        self.assertEqual(response.status_code, 200)


class download_exported_transactionsTests(TestCase):
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
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.setup = Setup.objects.create(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=True,
        )
        self.entity_setup = EntitySetup.objects.create(
            user=self.super_admin, entity=self.root, agents_setup=True, fees_setup=True
        )
        self.checker_user = CheckerUser(
            id=15, username='test_checker_user', root=self.root, user_type=2
        )
        self.checker_user.save()
        self.level = Levels(max_amount_can_be_disbursed=1200, created=self.root)
        self.level.save()
        self.checker_user.level = self.level
        self.checker_user.save()
        self.checker_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.checker_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.maker_user = MakerUser(
            id=14,
            username='test_maker_user',
            email='t@mk.com',
            root=self.root,
            user_type=1,
        )
        self.maker_user.is_staff = True
        self.maker_user.save()
        self.budget = Budget(disburser=self.root, current_balance=150)
        self.budget.save()
        fees_setup_bank_wallet = FeeSetup(
            budget_related=self.budget, issuer='bc', fee_type='f', fixed_value=20
        )
        fees_setup_bank_wallet.save()
        fees_setup_vodafone = FeeSetup(
            budget_related=self.budget, issuer='vf', fee_type='p', percentage_value=2.25
        )
        fees_setup_vodafone.save()

        # create doc, doc_review, DisbursementDocData, file category
        file_category = FileCategory.objects.create(user_created=self.root)
        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
        )
        doc_review = DocReview.objects.create(
            is_ok=True,
            doc=self.doc,
            user_created=self.checker_user,
        )
        disb_data_doc = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('disbursement:download_exported'))
        self.assertRedirects(response, '/user/login/')

    def test_forbidden_download(self):
        self.client.force_login(self.root)
        self.doc.is_disbursed = False
        self.doc.save()
        response = self.client.get(reverse('disbursement:download_exported'))
        self.assertEqual(response.status_code, 404)

    def test_file_not_exist(self):
        self.client.force_login(self.maker_user)
        response = self.client.get(
            f'/disburse/download_exported_transactions/?filename=test'
        )
        self.assertEqual(response.status_code, 404)

    def test_file_using_not_staff_user(self):
        self.client.force_login(self.root)
        response = self.client.get(
            f'/disburse/download_exported_transactions/?filename=test'
        )
        self.assertEqual(response.status_code, 403)

    def test_file_without_filename(self):
        self.client.force_login(self.maker_user)
        response = self.client.get(f'/disburse/download_exported_transactions/')
        self.assertEqual(response.status_code, 404)

    def test_file_exist(self):
        with open('/app/mediafiles/media/documents/disbursement/test.txt', 'w') as fp:
            pass
        self.client.force_login(self.maker_user)
        response = self.client.get(
            f'/disburse/download_exported_transactions/?filename=test.txt'
        )
        self.assertEqual(response.status_code, 200)


class HomeViewTest(TestCase):
    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = RootUser.objects.create(
            username="Careemn_Admin",
            email="integration_Admin@paymob.com",
            user_type=3,
            password=123456,
        )

        self.root.set_password("123456")
        self.root.save()
        self.root.root = self.root
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.brand = self.brand
        self.root.save()
        self.agent = Agent(msisdn='01021469732', wallet_provider=self.root, super=True)
        self.agent.save()
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="users", codename="accept_vodafone_onboarding"
            )
        )
        self.root.save()
        self.client_user = ClientModel(
            client=self.root, creator=self.super_admin, agents_onboarding_choice=0
        )
        self.client_user.save()
        self.setup = Setup.objects.create(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=True,
        )
        self.entity_setup = EntitySetup.objects.create(
            user=self.super_admin,
            entity=self.root,
            agents_setup=False,
            fees_setup=False,
        )

        self.request = RequestFactory()
        self.client = Client()
        self.makeruser = MakerUser.objects.create(
            username="makerUser1",
            root=self.root,
            user_type=1,
            email='user1112@gmail.com',
        )
        self.checkeruser = CheckerUser.objects.create(
            username="checkerUser1",
            root=self.root,
            user_type=2,
            email='user41112@gmail.com',
        )
        self.support_user = SupportUser.objects.create(
            username="support_user", email="support_user@gmail.com", user_type=8
        )
        self.support_user_setup = SupportSetup.objects.create(
            support_user=self.support_user, user_created=self.super_admin
        )

        self.instantapiviewer = InstantAPIViewerUser.objects.create(
            username="InstantAPIViewerUser1",
            root=self.root,
            user_type=7,
            email='user112@gmail.com',
        )
        self.instantapichecker = InstantAPICheckerUser.objects.create(
            username="InstantAPIcheckerUser1",
            root=self.root,
            user_type=7,
            email='userd112@gmail.com',
        )
        self.instantapiviewer.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='instant_model_onboarding'
            )
        )
        self.instanttransaction = InstantTransaction.objects.create(
            from_user=self.instantapichecker
        )
        self.instanttransaction.update_status_code_and_description()
        self.instanttransaction.issuer_type = InstantTransaction.VODAFONE
        self.instanttransaction.disbursed_date = datetime.datetime.now()
        self.instanttransaction.save()
        self.instanttransaction1 = InstantTransaction.objects.create(
            from_user=self.instantapichecker,
            issuer_type=InstantTransaction.ETISALAT,
            disbursed_date=datetime.datetime.now(),
        )
        self.instanttransaction1 = InstantTransaction.objects.create(
            from_user=self.instantapichecker,
            issuer_type=InstantTransaction.AMAN,
            disbursed_date=datetime.datetime.now(),
        )
        self.instanttransaction1 = InstantTransaction.objects.create(
            from_user=self.instantapichecker,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.datetime.now(),
        )
        self.instanttransaction1 = InstantTransaction.objects.create(
            from_user=self.instantapichecker,
            issuer_type=InstantTransaction.BANK_WALLET,
            disbursed_date=datetime.datetime.now(),
        )

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('disbursement:home_root'))
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('disbursement:home_root'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.instantapiviewer)
        response = self.client.get((reverse('disbursement:home_root')))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disbursement/home_root.html')

    def test_view_uses_query_parameter(self):
        self.client.force_login(self.instantapiviewer)
        response = self.client.get(
            '%s?export_issuer=wallets&export_start_date=2022-1-09&export_end_date=2022-1-11'
            % (reverse('disbursement:home_root'))
        )
        self.assertEqual(response.status_code, 302)

    def test_view_with_export_issuer_banks(self):
        self.client.force_login(self.instantapiviewer)
        response = self.client.get(
            '%s?export_issuer=banks&export_start_date=2022-1-09&export_end_date=2022-1-11'
            % (reverse('disbursement:home_root'))
        )
        self.assertEqual(response.status_code, 302)

    def test_view_with_export_issuer_vodafone_etisalat_aman(self):
        self.client.force_login(self.instantapiviewer)
        self.export_issuer = 'vodafone/etisalat/aman'
        response = self.client.get(
            f'%s?export_issuer={self.export_issuer}&export_start_date=2022-1-09&export_end_date=2022-1-11'
            % (reverse('disbursement:home_root'))
        )
        self.assertEqual(response.status_code, 302)

    def test_get_method_using_checkeruser(self):
        self.client.force_login(self.checkeruser)
        response = self.client.get(reverse('disbursement:home_root'))
        self.assertEqual(response.status_code, 200)

    def test_get_method_using_makeruser(self):
        self.client.force_login(self.makeruser)
        response = self.client.get((reverse('disbursement:home_root')))
        self.assertEqual(response.status_code, 200)


class DisbursementDataListViewTests(TestCase):
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
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.request = RequestFactory()
        self.client = Client()
        self.makeruser = MakerUser.objects.create(
            username="makerUser11",
            root=self.root,
            user_type=1,
            email='user11712@gmail.com',
        )
        self.checkeruser = CheckerUser.objects.create(
            username="checkerUser11",
            root=self.root,
            user_type=2,
            email='user411712@gmail.com',
        )
        self.makeruser.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.checkeruser.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('disbursement:vf_et_aman_list'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/home/portal-transactions/')
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('disbursement:vf_et_aman_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disbursement/vf_et_aman_trx_list.html')

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('disbursement:vf_et_aman_list'))
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name_for_maker(self):
        self.client.force_login(self.makeruser)
        response = self.client.get(reverse('disbursement:vf_et_aman_list'))
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name_for_checker(self):
        self.client.force_login(self.checkeruser)
        response = self.client.get(
            '%s?number=1&issuer=vodafone&start_date=2022-10-1&end_date=2022-11-1'
            % reverse('disbursement:vf_et_aman_list')
        )
        self.assertEqual(response.status_code, 200)


class OrangeBankWalletListViewTests(TestCase):
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
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.request = RequestFactory()
        self.client = Client()
        self.makeruser = MakerUser.objects.create(
            username="makerUser11",
            root=self.root,
            user_type=1,
            email='user11712@gmail.com',
        )
        self.checkeruser = CheckerUser.objects.create(
            username="checkerUser11",
            root=self.root,
            user_type=2,
            email='user411712@gmail.com',
        )
        self.makeruser.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.checkeruser.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('disbursement:orange_bank_wallet_list'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/home/portal-transactions-orange/')
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('disbursement:orange_bank_wallet_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'disbursement/orange_bank_wallet_trx_list.html'
        )

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('disbursement:orange_bank_wallet_list'))
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name_for_maker(self):
        self.client.force_login(self.makeruser)
        response = self.client.get(reverse('disbursement:orange_bank_wallet_list'))
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name_for_checker(self):
        self.client.force_login(self.checkeruser)
        response = self.client.get(
            '%s?number=1&issuer=vodafone&start_date=2022-10-1&end_date=2022-11-1'
            % reverse('disbursement:orange_bank_wallet_list')
        )
        self.assertEqual(response.status_code, 200)


class BanksListViewTests(TestCase):
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
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.request = RequestFactory()
        self.client = Client()
        self.makeruser = MakerUser.objects.create(
            username="makerUser11",
            root=self.root,
            user_type=1,
            email='user11712@gmail.com',
        )
        self.checkeruser = CheckerUser.objects.create(
            username="checkerUser11",
            root=self.root,
            user_type=2,
            email='user411712@gmail.com',
        )
        self.makeruser.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.checkeruser.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('disbursement:banks_list'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/home/portal-transactions-banks/')
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('disbursement:banks_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disbursement/banks_trx_list.html')

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('disbursement:banks_list'))
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name_for_maker(self):
        self.client.force_login(self.makeruser)
        response = self.client.get(reverse('disbursement:banks_list'))
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name_for_checker(self):
        self.client.force_login(self.checkeruser)
        response = self.client.get(
            '%s?number=1&account_number=114&start_date=2022-10-1&end_date=2022-11-1'
            % reverse('disbursement:banks_list')
        )
        self.assertEqual(response.status_code, 200)


class CreatePaymentLinkTests(TestCase):
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
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.request = RequestFactory()
        self.client = Client()
        self.makeruser = MakerUser.objects.create(
            username="makerUser11",
            root=self.root,
            user_type=1,
            email='user11712@gmail.com',
        )
        self.checkeruser = CheckerUser.objects.create(
            username="checkerUser11",
            root=self.root,
            user_type=2,
            email='user411712@gmail.com',
        )
        self.makeruser.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.checkeruser.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.setup = Setup(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=True,
        )
        self.setup.save()
        self.budget = Budget(disburser=self.root)
        self.budget.save()
        fees_setup_bank_wallet = FeeSetup(
            budget_related=self.budget, issuer='bc', fee_type='f', fixed_value=20
        )
        fees_setup_bank_wallet.save()
        fees_setup_vodafone = FeeSetup(
            budget_related=self.budget, issuer='vf', fee_type='p', percentage_value=2.25
        )
        fees_setup_vodafone.save()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('disbursement:create_payment_link'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/create/payment-link/')
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('disbursement:create_payment_link'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disbursement/payment_link_list.html')

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('disbursement:create_payment_link'))
        self.assertEqual(response.status_code, 200)

    def test_post_method_with_error(self):
        self.client.force_login(self.root)
        data = {
            "amount": 100,
            "pin": "123456",
        }
        response = self.client.post((reverse('disbursement:create_payment_link')), data)
        self.assertEqual(response.status_code, 200)

    def test_post_method(self):
        self.budget.current_balance = 1000
        self.budget.save()
        self.client.force_login(self.root)
        data = {
            "amount": 100,
            "pin": "123456",
        }
        response = self.client.post((reverse('disbursement:create_payment_link')), data)
        self.assertEqual(response.status_code, 302)


class DisbursePaymentLinkTests(TestCase):
    def setUp(self):
        self.token = AccessToken()
        self.token.save()
        self.super_admin = SuperAdminUserFactory()

        payment_link = PaymentLink.objects.create(
            link='test',
            amount=100,
            token=self.token.token,
            created_by=self.super_admin,
        )

    def test_view_url_accessible_by_name(self):
        response = self.client.get(
            reverse(
                'disbursement:disburse_payment_link',
                kwargs={'payment_token': self.token.token},
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_get_method_with_token_not_exist(self):
        self.token.used = True
        self.token.save()
        response = self.client.get(
            reverse(
                'disbursement:disburse_payment_link',
                kwargs={'payment_token': self.token.token},
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(
            reverse(
                'disbursement:disburse_payment_link',
                kwargs={'payment_token': self.token.token},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'disbursement/disburse_payment_link.html')

    @patch("requests.post", return_value=SingleStepTransactionMockResponse_Successful())
    def test_post_method_on_bankcard(self, mocked):

        data = {
            "amount": 100,
            "issuer": "bank_card",
            "creditor_account_number": '4665543567987643',
            "creditor_name": "test test",
            "creditor_bank": "AUB",
            "transaction_type": "CASH_TRANSFER",
        }
        response = self.client.post(
            reverse(
                'disbursement:disburse_payment_link',
                kwargs={'payment_token': self.token.token},
            ),
            data,
        )
        self.assertEqual(response.status_code, 200)

    @patch("requests.post", return_value=SingleStepTransactionMockResponse_Successful())
    def test_post_method_on_vodafone(self, mocked):

        data = {
            "amount": 100,
            "issuer": "vodafone",
            "msisdn": '01021469732',
        }
        response = self.client.post(
            reverse(
                'disbursement:disburse_payment_link',
                kwargs={'payment_token': self.token.token},
            ),
            data,
        )
        self.assertEqual(response.status_code, 200)

    @patch("requests.post", return_value=SingleStepTransactionMockResponse_Successful())
    def test_post_method_on_etisalat(self, mocked):

        data = {
            "amount": 100,
            "issuer": "etisalat",
            "msisdn": '01021469732',
        }
        response = self.client.post(
            reverse(
                'disbursement:disburse_payment_link',
                kwargs={'payment_token': self.token.token},
            ),
            data,
        )
        self.assertEqual(response.status_code, 200)

    @patch("requests.post", return_value=SingleStepTransactionMockResponse_Successful())
    def test_post_method_on_bank_wallet(self, mocked):

        data = {
            "amount": 100,
            "issuer": "bank_wallet",
            "msisdn": '01021469732',
            'full_name': 'test',
        }
        response = self.client.post(
            reverse(
                'disbursement:disburse_payment_link',
                kwargs={'payment_token': self.token.token},
            ),
            data,
        )
        self.assertEqual(response.status_code, 200)

    @patch("requests.post", return_value=SingleStepTransactionMockResponse_Successful())
    def test_post_method_on_orange(self, mocked):

        data = {
            "amount": 100,
            "issuer": "orange",
            "msisdn": '01021469732',
            'full_name': 'test',
        }
        response = self.client.post(
            reverse(
                'disbursement:disburse_payment_link',
                kwargs={'payment_token': self.token.token},
            ),
            data,
        )
        self.assertEqual(response.status_code, 200)

    @patch("requests.post", return_value=SingleStepTransactionMockResponse_Successful())
    def test_post_method_on_aman(self, mocked):

        data = {
            "amount": 100,
            "issuer": "aman",
            "msisdn": '01021469732',
            'first_name': 'test',
            'last_name': 'test',
            'email': 'test@gmail.com',
        }
        response = self.client.post(
            reverse(
                'disbursement:disburse_payment_link',
                kwargs={'payment_token': self.token.token},
            ),
            data,
        )
        self.assertEqual(response.status_code, 200)

    @patch("requests.post", return_value=SingleStepTransactionMockResponse_failed())
    def test_post_method_on_bank_wallet_with_failed_response(self, mocked):

        data = {
            "amount": 100,
            "issuer": "bank_wallet",
            "msisdn": '01021469732',
            'full_name': 'test',
        }
        response = self.client.post(
            reverse(
                'disbursement:disburse_payment_link',
                kwargs={'payment_token': self.token.token},
            ),
            data,
        )
        self.assertEqual(response.status_code, 200)

    @patch("requests.post", return_value=None)
    def test_post_method_on_bank_wallet_with_eception(self, mocked):

        data = {
            "amount": 100,
            "issuer": "bank_wallet",
            "msisdn": '01021469732',
            'full_name': 'test',
        }
        response = self.client.post(
            reverse(
                'disbursement:disburse_payment_link',
                kwargs={'payment_token': self.token.token},
            ),
            data,
        )
        self.assertEqual(response.status_code, 200)
