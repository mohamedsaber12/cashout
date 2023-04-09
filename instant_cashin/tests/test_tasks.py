# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import os
from unittest import mock
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.test import TestCase

from data.models import Doc, DocReview, FileCategory
from disbursement.models import (BankTransaction, DisbursementData,
                                 DisbursementDocData)
# from django.utils.timezone import datetime
from instant_cashin.models import InstantTransaction
from instant_cashin.tasks import (
    check_for_status_updates_for_latest_bank_transactions,
    check_for_status_updates_for_latest_bank_transactions_more_than_6_days,
    disburse_accept_pending_transactions,
    self_update_bank_transactions_staging,
    update_instant_timeouts_from_vodafone_report)
from instant_cashin.utils import get_from_env
from users.models import Brand, CheckerUser
from users.models import Client as ClientModel
from users.models import Levels, MakerUser
from users.tests.factories import (AdminUserFactory, SuperAdminUserFactory,
                                   VMTDataFactory)
from utilities.models import AbstractBaseDocType, Budget, FeeSetup


class StatusUpdatesForLatestBankTransactionsTests(TestCase):
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
        doc_review = DocReview.objects.create(
            is_ok=True,
            doc=self.doc,
            user_created=self.checker_user,
        )
        disb_data_doc = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )

        self.doc.type_of = AbstractBaseDocType.E_WALLETS
        self.doc.save()

        self.banktransaction_pending = BankTransaction.objects.create(
            currency="EGP",
            debtor_address_1="EG",
            creditor_address_1="EG",
            corporate_code=get_from_env("ACH_CORPORATE_CODE"),
            debtor_account=get_from_env("ACH_DEBTOR_ACCOUNT"),
            document=self.doc,
            user_created=self.doc.owner,
            amount='1000',
            creditor_name='test',
            creditor_account_number='545115151515',
            creditor_bank='bankmisr',
            category_code="CASH",
            purpose="CASH",
            fees='100',
            vat='50',
            status='P',
            comment1="",
            comment2="",
            disbursed_date=datetime.datetime.now(),
        )

    @mock.patch.dict(os.environ, {"ach_worker": "celery@5934f077109e"})
    def test_check_for_status_updates_for_latest_bank_transactions(self):
        os.environ.setdefault('ach_worker', 'celery@5934f077109e')
        self.assertTrue(
            check_for_status_updates_for_latest_bank_transactions(days_delta=6)
        )

    @mock.patch.dict(os.environ, {"ach_worker": "celery@5934f077109e"})
    def test_check_for_status_updates_for_latest_bank_transactions_more_than_6_days(
        self,
    ):
        os.environ.setdefault('ach_worker', 'celery@5934f077109e')
        self.assertTrue(
            check_for_status_updates_for_latest_bank_transactions_more_than_6_days()
        )


class MockResponse:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = True

    def json(self):
        return {
            "success": True,
        }


class update_instant_timeouts_from_vodafone_report_Tests(TestCase):
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
        self.budget = Budget(disburser=self.root, current_balance=250)
        self.budget.save()
        fees_setup_bank_card = FeeSetup(
            budget_related=self.budget, issuer='bc', fee_type='f', fixed_value=20
        )
        fees_setup_bank_card.save()
        fees_setup_bank_wallet = FeeSetup(
            budget_related=self.budget, issuer='bw', fee_type='p', fixed_value=2.0
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
        fees_setup_etisalat = FeeSetup(
            budget_related=self.budget, issuer='es', fee_type='p', percentage_value=2.25
        )
        fees_setup_etisalat.save()
        fees_setup_aman = FeeSetup(
            budget_related=self.budget, issuer='am', fee_type='p', percentage_value=2.25
        )
        fees_setup_aman.save()

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
        doc_review = DocReview.objects.create(
            is_ok=True,
            doc=self.doc,
            user_created=self.checker_user,
        )
        disb_data_doc = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )

        self.doc.type_of = AbstractBaseDocType.E_WALLETS
        self.doc.save()
        self.instanttransaction = InstantTransaction.objects.create(
            from_user=self.checker_user
        )
        self.instanttransaction.update_status_code_and_description()
        self.instanttransaction.issuer_type = InstantTransaction.VODAFONE
        self.instanttransaction.disbursed_date = datetime.datetime.now()
        self.instanttransaction.save()
        self.instanttransaction1 = InstantTransaction.objects.create(
            transaction_status_code='6005',
            status="U",
            reference_id='003145007023',
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ETISALAT,
            disbursed_date=datetime.datetime.now(),
        )
        self.instanttransaction1 = InstantTransaction.objects.create(
            transaction_status_code='6005',
            status="U",
            from_accept='single',
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.datetime.now(),
        )
        self.instanttransaction1 = InstantTransaction.objects.create(
            transaction_status_code='6005',
            status="U",
            reference_id='053145007023',
            from_accept='single',
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.datetime.now(),
        )
        self.instanttransaction1 = InstantTransaction.objects.create(
            transaction_status_code='6005',
            status="U",
            from_accept='single',
            reference_id='00145007023',
            from_user=self.checker_user,
            issuer_type=InstantTransaction.BANK_WALLET,
            disbursed_date=datetime.datetime.now(),
        )

    @mock.patch.dict(
        os.environ,
        {"DECLINE_SINGLE_STEP_URL": "http://test", 'SINGLE_STEP_TOKEN': 'test'},
    )
    @patch("requests.post", return_value=MockResponse())
    def test_update_bank_transactions_staging(self, mocked):
        self.assertIsNone(
            update_instant_timeouts_from_vodafone_report(
                {
                    '003145007023': {
                        'wallet': '00201018073852',
                        'success': True,
                        'amount': 30.43,
                    },
                    '053145007023': {
                        'wallet': '00201018073852',
                        'success': False,
                        'amount': 30.43,
                    },
                },
                datetime.datetime.now().strftime("%Y-%m-%d"),
                datetime.datetime.now().strftime("%Y-%m-%d"),
                'fathyyehia@paymob.com',
            )
        )


class update_instant_timeouts_from_vodafone_report_Tests(TestCase):
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
        self.super_admin.save()
        self.maker_user.save()
        self.budget = Budget(disburser=self.root, current_balance=250)
        self.budget.save()
        fees_setup_bank_card = FeeSetup(
            budget_related=self.budget, issuer='bc', fee_type='f', fixed_value=20
        )
        fees_setup_bank_card.save()
        fees_setup_bank_wallet = FeeSetup(
            budget_related=self.budget, issuer='bw', fee_type='p', fixed_value=2.0
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
        fees_setup_etisalat = FeeSetup(
            budget_related=self.budget, issuer='es', fee_type='p', percentage_value=2.25
        )
        fees_setup_etisalat.save()
        fees_setup_aman = FeeSetup(
            budget_related=self.budget, issuer='am', fee_type='p', percentage_value=2.25
        )
        fees_setup_aman.save()

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
        doc_review = DocReview.objects.create(
            is_ok=True,
            doc=self.doc,
            user_created=self.checker_user,
        )
        disb_data_doc = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )

        self.doc.type_of = AbstractBaseDocType.BANK_CARDS
        self.doc.save()
        self.banktransaction_success = BankTransaction.objects.create(
            currency="EGP",
            debtor_address_1="EG",
            creditor_address_1="EG",
            corporate_code=get_from_env("ACH_CORPORATE_CODE"),
            debtor_account=get_from_env("ACH_DEBTOR_ACCOUNT"),
            document=self.doc,
            user_created=self.doc.owner,
            amount='1000',
            creditor_name='test',
            creditor_account_number='545115151515',
            creditor_bank='bankmisr',
            category_code="CASH",
            purpose="CASH",
            fees='100',
            vat='50',
            status='S',
            comment1="",
            comment2="",
            disbursed_date=datetime.datetime.now(),
            transaction_status_code=8000,
        )
        self.banktransaction_success = BankTransaction.objects.create(
            currency="EGP",
            debtor_address_1="EG",
            creditor_address_1="EG",
            corporate_code=get_from_env("ACH_CORPORATE_CODE"),
            debtor_account=get_from_env("ACH_DEBTOR_ACCOUNT"),
            document=self.doc,
            user_created=self.doc.owner,
            amount='1000',
            creditor_name='test',
            creditor_account_number='545115151515',
            creditor_bank='bankmisr',
            category_code="CASH",
            purpose="CASH",
            fees='100',
            vat='50',
            status='S',
            comment1="",
            comment2="",
            disbursed_date=datetime.datetime.now(),
            transaction_status_code=8111,
        )
        self.banktransaction_success = BankTransaction.objects.create(
            currency="EGP",
            debtor_address_1="EG",
            creditor_address_1="EG",
            corporate_code=get_from_env("ACH_CORPORATE_CODE"),
            debtor_account=get_from_env("ACH_DEBTOR_ACCOUNT"),
            document=self.doc,
            user_created=self.doc.owner,
            amount='1000',
            creditor_name='test',
            creditor_account_number='545115151515',
            creditor_bank='bankmisr',
            category_code="CASH",
            purpose="CASH",
            fees='100',
            vat='50',
            status='S',
            comment1="",
            comment2="",
            disbursed_date=datetime.datetime.now(),
            transaction_status_code=8333,
        )
        self.banktransaction_success = BankTransaction.objects.create(
            currency="EGP",
            debtor_address_1="EG",
            creditor_address_1="EG",
            corporate_code=get_from_env("ACH_CORPORATE_CODE"),
            debtor_account=get_from_env("ACH_DEBTOR_ACCOUNT"),
            document=self.doc,
            user_created=self.doc.owner,
            amount='1000',
            creditor_name='test',
            creditor_account_number='545115151515',
            creditor_bank='bankmisr',
            category_code="CASH",
            purpose="CASH",
            fees='100',
            vat='50',
            status='S',
            comment1="",
            comment2="",
            disbursed_date=datetime.datetime.now(),
        )

    @mock.patch.dict(
        os.environ,
        {"DECLINE_SINGLE_STEP_URL": "http://test", 'SINGLE_STEP_TOKEN': 'test'},
    )
    @patch("requests.post", return_value=MockResponse())
    def test_self_update_bank_transactions_staging(self, mocked):
        self.assertIsNone(self_update_bank_transactions_staging())


class MockResponse_with_TXNSTATUS_300:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = True

    def json(self):
        return {'TXNSTATUS': '300', 'TXNID': '1555', 'MESSAGE': 'test', 'success': True}


class MockResponse:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = True

    def json(self):
        return {'success': True}


class mock_response_with_TXNSTATUS_200:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = True

    def json(self):
        return {'TXNSTATUS': '200', 'TXNID': '1555', 'MESSAGE': 'test', 'success': True}


class mock_response_with_TXNSTATUS_501:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = True

    def json(self):
        return {
            'TXNSTATUS': '501',
            'TXNID': '54555',
            'MESSAGE': 'test',
            'success': True,
        }


class disburse_accept_pending_transactions_Tests(TestCase):
    def setUp(self):
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
        self.budget = Budget(disburser=self.root, current_balance=250)
        self.budget.save()
        fees_setup_bank_card = FeeSetup(
            budget_related=self.budget, issuer='bc', fee_type='f', fixed_value=20
        )
        fees_setup_bank_card.save()
        fees_setup_bank_wallet = FeeSetup(
            budget_related=self.budget, issuer='bw', fee_type='p', fixed_value=2.0
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
        fees_setup_etisalat = FeeSetup(
            budget_related=self.budget, issuer='es', fee_type='p', percentage_value=2.25
        )
        fees_setup_etisalat.save()
        fees_setup_aman = FeeSetup(
            budget_related=self.budget, issuer='am', fee_type='p', percentage_value=2.25
        )
        fees_setup_aman.save()

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
        doc_review = DocReview.objects.create(
            is_ok=True,
            doc=self.doc,
            user_created=self.checker_user,
        )
        disb_data_doc = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )

        self.doc.type_of = AbstractBaseDocType.E_WALLETS
        self.doc.save()
        self.instanttransaction = InstantTransaction.objects.create(
            from_user=self.checker_user
        )
        self.instanttransaction.update_status_code_and_description()
        self.instanttransaction.issuer_type = InstantTransaction.VODAFONE
        self.instanttransaction.disbursed_date = datetime.datetime.now()
        self.instanttransaction.save()
        for field in InstantTransaction._meta.local_fields:
            if hasattr(field, 'auto_now'):
                field.auto_now = False
            if hasattr(field, 'auto_now_add'):
                field.auto_now_add = False
            self.instanttransaction1 = InstantTransaction.objects.create(
                transaction_status_code='6005',
                status="P",
                reference_id='003145007023',
                from_accept='single',
                from_user=self.checker_user,
                issuer_type=InstantTransaction.ETISALAT,
                created_at=(datetime.datetime.now() - datetime.timedelta(hours=3)),
                disbursed_date=(datetime.datetime.now() - datetime.timedelta(hours=3)),
            )
            self.instanttransaction1 = InstantTransaction.objects.create(
                transaction_status_code='6005',
                status="P",
                from_accept='single',
                from_user=self.checker_user,
                issuer_type=InstantTransaction.ORANGE,
                created_at=(datetime.datetime.now() - datetime.timedelta(hours=3)),
                disbursed_date=(datetime.datetime.now() - datetime.timedelta(hours=3)),
            )
            self.instanttransaction1 = InstantTransaction.objects.create(
                transaction_status_code='6005',
                status="P",
                reference_id='053145007023',
                from_accept='single',
                from_user=self.checker_user,
                issuer_type=InstantTransaction.ORANGE,
                created_at=(datetime.datetime.now() - datetime.timedelta(hours=3)),
                disbursed_date=(datetime.datetime.now() - datetime.timedelta(hours=3)),
            )
            self.instanttransaction1 = InstantTransaction.objects.create(
                transaction_status_code='6005',
                status="P",
                from_accept='single',
                reference_id='00145007023',
                from_user=self.checker_user,
                issuer_type=InstantTransaction.BANK_WALLET,
                created_at=(datetime.datetime.now() - datetime.timedelta(hours=3)),
                disbursed_date=(datetime.datetime.now() - datetime.timedelta(hours=3)),
            )

    @patch("requests.post", return_value=MockResponse())
    @mock.patch.dict(
        os.environ,
        {"DECLINE_SINGLE_STEP_URL": "http://test", 'SINGLE_STEP_TOKEN': 'test'},
    )
    def test_disburse_accept_pending_transactions(self, mocked):
        os.environ.setdefault(f'{self.super_admin.username}_VODAFONE_PIN', '123456')
        self.assertIsNone(disburse_accept_pending_transactions())

    @patch("requests.post", return_value=mock_response_with_TXNSTATUS_200())
    @mock.patch.dict(
        os.environ,
        {"DECLINE_SINGLE_STEP_URL": "http://test", 'SINGLE_STEP_TOKEN': 'test'},
    )
    def test_disburse_accept_pending_transactions_with_TXNSTATUS_200(self, mocked):
        os.environ.setdefault(f'{self.super_admin.username}_VODAFONE_PIN', '123456')
        self.assertIsNone(disburse_accept_pending_transactions())

    @patch("requests.post", return_value=mock_response_with_TXNSTATUS_501())
    @mock.patch.dict(
        os.environ,
        {"DECLINE_SINGLE_STEP_URL": "http://test", 'SINGLE_STEP_TOKEN': 'test'},
    )
    def test_disburse_accept_pending_transactions_with_TXNSTATUS_501(self, mocked):
        os.environ.setdefault(f'{self.super_admin.username}_VODAFONE_PIN', '123456')
        self.assertIsNone(disburse_accept_pending_transactions())

    @patch("requests.post", return_value=MockResponse_with_TXNSTATUS_300())
    @mock.patch.dict(
        os.environ,
        {"DECLINE_SINGLE_STEP_URL": "http://test", 'SINGLE_STEP_TOKEN': 'test'},
    )
    def test_disburse_accept_pending_transactions_with_TXNSTATUS_300(self, mocked):
        os.environ.setdefault(f'{self.super_admin.username}_VODAFONE_PIN', '123456')
        self.assertIsNone(disburse_accept_pending_transactions())

    # @patch("requests.post", return_value=MockResponse_with_TXNSTATUS_300())
    # @mock.patch.dict(os.environ, {"DECLINE_SINGLE_STEP_URL": "http://test", 'SINGLE_STEP_TOKEN': 'test'})
    def test_disburse_accept_pending_transactions_with_TimeoutError(self):
        self.vmt_data_obj.vmt_environment = 'test'
        os.environ.setdefault(f'{self.super_admin.username}_VODAFONE_PIN', '123456')
        self.assertIsNone(disburse_accept_pending_transactions())
