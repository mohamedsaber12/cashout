# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from data.models import Doc, FileCategory
from data.models.filecategory import FileCategory
from disbursement.models import (Agent, BankTransaction, DisbursementData,
                                 DisbursementDocData, RemainingAmounts,
                                 VMTData)
from instant_cashin.models import InstantTransaction
from instant_cashin.specific_issuers_integrations.ach.instant_cashin import \
    BankTransactionsChannel
from instant_cashin.utils import get_from_env
from users.models import Brand, CheckerUser
from users.models import Client as ClientModel
from users.models import Levels, MakerUser
from users.tests.factories import (AdminUserFactory, InstantAPICheckerFactory,
                                   InstantAPIViewerUserFactory,
                                   SuperAdminUserFactory, VMTDataFactory)
from utilities.models import (AbstractBaseDocType, Budget,
                              CallWalletsModerator, FeeSetup)


class InstantTransactionsListViewTests(TestCase):
    def setUp(self):
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.root.save()

        # create dashboard user
        self.dashboard_user = InstantAPIViewerUserFactory(user_type=7, root=self.root)
        self.dashboard_user.set_password('fiA#EmkjLBh9VSXy6XvFKxnR9jXt')
        self.dashboard_user.save()
        self.dashboard_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='instant_model_onboarding'
            )
        )

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
        self.dashboard_user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='instant_model_onboarding'
            )
        )

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


class MockResponse:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = True

    def json(self):
        return {'TXNSTATUS': '400'}


class BankTransactionsChannelTests(TestCase):
    def setUp(self):
        super().setUp()
        # create root
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
        self.root.callback_url = " http://www.google.com"
        self.root.save()
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
        self.super_admin.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
            )
        )
        self.super_admin.save()
        self.maker_user = MakerUser(
            hierarchy=1,
            id=14,
            username='test_maker_user',
            email='t@mk.com',
            root=self.root,
            user_type=1,
        )
        self.maker_user.save()
        self.budget = Budget(disburser=self.root, current_balance=250)
        self.budget.save()
        fees_setup_bank_wallet = FeeSetup(
            budget_related=self.budget, issuer='bc', fee_type='f', fixed_value=20
        )
        fees_setup_bank_wallet.save()
        fees_setup_vodafone = FeeSetup(
            budget_related=self.budget, issuer='vf', fee_type='p', percentage_value=2.25
        )
        fees_setup_vodafone.save()
        fees_setup_orange = FeeSetup(
            budget_related=self.budget, issuer='og', fee_type='p', percentage_value=2.25
        )
        fees_setup_orange.save()

        file_category = FileCategory.objects.create(
            user_created=self.root, no_of_reviews_required=1
        )
        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=file_category,
            is_disbursed=False,
            can_be_disbursed=True,
            is_processed=True,
            disbursed_by=self.checker_user,
        )
        self.bank_trx_obj = BankTransaction.objects.create(
            currency="EGP",
            debtor_address_1="EG",
            creditor_address_1="EG",
            corporate_code=get_from_env("ACH_CORPORATE_CODE"),
            debtor_account=get_from_env("ACH_DEBTOR_ACCOUNT"),
            document=self.doc,
            user_created=self.doc.owner,
            amount='1000',
            creditor_name='test',
            creditor_account_number='01211409281',
            creditor_bank='bankmisr',
            category_code="CASH",
            purpose="CASH",
            fees='100',
            vat='50',
            status='S',
            comment1="",
            comment2="",
            end_to_end=12345,
            disbursed_date=datetime.now(),
        )

    def test_create_new_trx_out_of_passed_one(self):
        self.assertNotEqual(
            BankTransactionsChannel.create_new_trx_out_of_passed_one(self.bank_trx_obj),
            '',
        )

    def test_get_corresponding_instant_trx_if_any(self):
        self.assertFalse(
            BankTransactionsChannel.get_corresponding_instant_trx_if_any(
                self.bank_trx_obj
            ),
            '',
        )

    def test_get_corresponding_instant_trx_if_any_and_transaction_not_end_to_end(self):
        self.bank_trx_obj.end_to_end = False
        self.bank_trx_obj.save()
        self.assertFalse(
            BankTransactionsChannel.get_corresponding_instant_trx_if_any(
                self.bank_trx_obj
            ),
            '',
        )

    # TODO error

    # @patch("SSLCertificate", return_value="test")
    # def test_accumulate_send_transaction_payload(self, mocked):
    #     with mocked.patch.object(__builtin__, 'SSLCertificate') as mock:
    #         mock.return_value = 'unittest_output'
    #         self.assertFalse(
    #             BankTransactionsChannel.accumulate_send_transaction_payload(
    #                 self.bank_trx_obj
    #             ),
    #             '',
    #         )

    # @patch("SSLCertificate", return_value="test")
    # def test_accumulate_get_transaction_status_payload(self, mocked):
    #     self.assertFalse(BankTransactionsChannel.accumulate_get_transaction_status_payload(self.bank_trx_obj), '')
    @patch("requests.post", return_value=MockResponse())
    def test_post(self, mocked):
        self.assertNotEqual(
            BankTransactionsChannel.post(
                get_from_env("EBC_API_URL"), {}, self.bank_trx_obj
            ),
            '',
        )

    @patch("requests.get", return_value=MockResponse())
    def test_get(self, mocked):
        self.assertNotEqual(
            BankTransactionsChannel.get(
                get_from_env("EBC_API_URL"), {}, self.bank_trx_obj
            ),
            '',
        )

    def test_map_response_code_and_message(self):
        self.instanttransaction = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='P',
        )
        json_response = {'ResponseCode': '8000'}
        self.assertNotEqual(
            BankTransactionsChannel.map_response_code_and_message(
                self.bank_trx_obj, self.instanttransaction, json_response, 1000
            ),
            '',
        )

    def test_map_response_code_and_message_with_ResponseCode_8001(self):
        self.instanttransaction = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='P',
        )
        json_response = {'ResponseCode': '8001'}
        self.assertNotEqual(
            BankTransactionsChannel.map_response_code_and_message(
                self.bank_trx_obj, self.instanttransaction, json_response, 1000
            ),
            '',
        )

    def test_map_response_code_and_message_with_ResponseCode_8002(self):
        self.instanttransaction = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='P',
        )
        json_response = {'ResponseCode': '8002'}
        self.assertNotEqual(
            BankTransactionsChannel.map_response_code_and_message(
                self.bank_trx_obj, self.instanttransaction, json_response, 1000
            ),
            '',
        )

    def test_map_response_code_and_message_with_ResponseCode_8003(self):
        self.instanttransaction = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='P',
        )
        json_response = {'ResponseCode': '8003'}
        self.assertNotEqual(
            BankTransactionsChannel.map_response_code_and_message(
                self.bank_trx_obj, self.instanttransaction, json_response, 1000
            ),
            '',
        )

    def test_map_response_code_and_message_with_ResponseCode_other(self):
        self.instanttransaction = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='P',
        )
        json_response = {'ResponseCode': '800'}
        self.assertNotEqual(
            BankTransactionsChannel.map_response_code_and_message(
                self.bank_trx_obj, self.instanttransaction, json_response, 1000
            ),
            '',
        )

    def test_map_response_code_and_message_with_ResponseCode_8111(self):
        self.instanttransaction = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='P',
        )
        json_response = {'ResponseCode': '8111'}
        self.assertNotEqual(
            BankTransactionsChannel.map_response_code_and_message(
                self.bank_trx_obj, self.instanttransaction, json_response, 1000
            ),
            '',
        )

    def test_update_bank_trx_status(self):
        json_response = {
            'TransactionStatusCode': '8111',
            'TransactionStatusDescription': 'test',
        }
        self.assertNotEqual(
            BankTransactionsChannel.update_bank_trx_status(
                self.bank_trx_obj, json_response
            ),
            '',
        )

    def test_update_bank_trx_status_TransactionStatusCode_8222(self):
        json_response = {
            'TransactionStatusCode': '8222',
            'TransactionStatusDescription': 'test',
        }
        self.assertNotEqual(
            BankTransactionsChannel.update_bank_trx_status(
                self.bank_trx_obj, json_response
            ),
            '',
        )

    def test_update_bank_trx_status_TransactionStatusCode_rejected(self):
        json_response = {
            'TransactionStatusCode': '000001',
            'TransactionStatusDescription': 'test',
        }
        self.assertNotEqual(
            BankTransactionsChannel.update_bank_trx_status(
                self.bank_trx_obj, json_response
            ),
            '',
        )

    def test_update_bank_trx_status_TransactionStatusCode_returned(self):
        self.instanttransaction = InstantTransaction.objects.create(
            uid=12345,
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='P',
        )
        json_response = {
            'TransactionStatusCode': '000100',
            'TransactionStatusDescription': 'test',
        }
        self.assertNotEqual(
            BankTransactionsChannel.update_bank_trx_status(
                self.bank_trx_obj, json_response
            ),
            '',
        )

    def test_send_transaction(self):
        self.instanttransaction = InstantTransaction.objects.create(
            uid=12345,
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='P',
        )
        self.assertNotEqual(
            BankTransactionsChannel.send_transaction(
                self.bank_trx_obj, self.instanttransaction, 1000
            ),
            '',
        )

    def test_send_transaction_issuer_bank_card(self):
        self.instanttransaction = InstantTransaction.objects.create(
            uid=12345,
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='P',
        )
        self.assertNotEqual(
            BankTransactionsChannel.send_transaction(self.bank_trx_obj, None, 1000), ''
        )

    def test_send_transaction_for_root_UVAAdmin(self):
        self.root.username = 'UVA-Admin'
        self.root.save()
        remaining_amounts = RemainingAmounts.objects.create(
            mobile='01211409281',
            full_name='fathi yehia',
            base_amount=10000,
            remaining_amount=10000,
        )
        self.instanttransaction = InstantTransaction.objects.create(
            uid=12345,
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='P',
        )
        self.assertNotEqual(
            BankTransactionsChannel.send_transaction(self.bank_trx_obj, None, 1000), ''
        )

    def test_send_transaction_for_root_UVAAdmin_but_amount_greater_than_remaining_amount(
        self,
    ):
        self.root.username = 'UVA-Admin'
        self.root.save()
        self.bank_trx_obj.amount = 15000
        self.bank_trx_obj.save()
        remaining_amounts = RemainingAmounts.objects.create(
            mobile='01211409281',
            full_name='fathi yehia',
            base_amount=10000,
            remaining_amount=10000,
        )
        self.instanttransaction = InstantTransaction.objects.create(
            uid=12345,
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='P',
        )
        self.assertNotEqual(
            BankTransactionsChannel.send_transaction(self.bank_trx_obj, None, 1000), ''
        )

    def test_get_transaction_status(self):
        self.assertNotEqual(
            BankTransactionsChannel.get_transaction_status(self.bank_trx_obj), ''
        )

    def test_update_manual_batch_transactions(self):
        self.assertNotEqual(
            BankTransactionsChannel.update_manual_batch_transactions(
                [
                    {
                        "transaction_id": self.bank_trx_obj.transaction_id,
                        'status': 'Settled Final',
                    }
                ]
            ),
            '',
        )

    def test_update_manual_batch_transactions_with_status_Settled_Opened_For_Return(
        self,
    ):
        self.assertNotEqual(
            BankTransactionsChannel.update_manual_batch_transactions(
                [
                    {
                        "transaction_id": self.bank_trx_obj.transaction_id,
                        'status': 'Settled ,Opened For Return',
                    }
                ]
            ),
            '',
        )

    def test_update_manual_batch_transactions_with_status_Returned_Finaln(self):
        self.assertNotEqual(
            BankTransactionsChannel.update_manual_batch_transactions(
                [
                    {
                        "transaction_id": self.bank_trx_obj.transaction_id,
                        'status': 'Returned Final',
                    }
                ]
            ),
            '',
        )

    def test_update_manual_batch_transactions_with_status_Rejected_Final(self):
        self.assertNotEqual(
            BankTransactionsChannel.update_manual_batch_transactions(
                [
                    {
                        "transaction_id": self.bank_trx_obj.transaction_id,
                        'status': 'Rejected Final',
                    }
                ]
            ),
            '',
        )

    def test_update_manual_batch_transactions_with_status_Accepted(self):
        self.assertNotEqual(
            BankTransactionsChannel.update_manual_batch_transactions(
                [
                    {
                        "transaction_id": self.bank_trx_obj.transaction_id,
                        'status': 'Accepted',
                    }
                ]
            ),
            '',
        )

    def test_update_manual_batch_transactions_with_status_else(self):
        self.assertNotEqual(
            BankTransactionsChannel.update_manual_batch_transactions(
                [{"transaction_id": self.bank_trx_obj.transaction_id, 'status': 'else'}]
            ),
            '',
        )

    def test_update_manual_batch_transactions_with_status_exception(self):
        self.assertNotEqual(
            BankTransactionsChannel.update_manual_batch_transactions(
                [{"transaction_id": 15, 'status': 'else'}]
            ),
            '',
        )
