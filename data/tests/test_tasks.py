from __future__ import unicode_literals

import os
from datetime import timedelta
from unittest.mock import patch

import pandas as pd
from django.contrib.auth.models import Permission
from django.test import TestCase
# import datetime
from django.utils.timezone import datetime

from data.models import Doc, DocReview, FileCategory
from data.tasks import (BankWalletsAndCardsSheetProcessor,
                        EWalletsSheetProcessor,
                        ExportClientsTransactionsMonthlyReportTask,
                        ExportPortalRootOrDashboardUserTransactionsBanks,
                        ExportPortalRootOrDashboardUserTransactionsEwallets,
                        ExportPortalRootTransactionsEwallet,
                        create_recuring_docs, doc_review_maker_mail,
                        generate_all_disbursed_data,
                        generate_failed_disbursed_data,
                        generate_success_disbursed_data,
                        generate_vf_daily_report,
                        handle_change_profile_callback, notify_checkers,
                        notify_disbursers, notify_maker)
from disbursement.models import (Agent, BankTransaction, DisbursementData,
                                 DisbursementDocData)
from disbursement.tasks import (BulkDisbursementThroughOneStepCashin,
                                check_for_late_change_profile_callback,
                                check_for_late_disbursement_callback)
from instant_cashin.models import InstantTransaction
from instant_cashin.utils import get_from_env
from users.models import Brand, CheckerUser
from users.models import Client as ClientModel
from users.models import Levels, MakerUser
from users.models.entity_setup import EntitySetup
from users.tests.factories import (AdminUserFactory, SuperAdminUserFactory,
                                   VMTDataFactory)
from utilities.models import AbstractBaseDocType, Budget, FeeSetup
from utilities.models.generic_models import CallWalletsModerator


class TestBankWalletsAndCardsSheetProcessor(TestCase):
    def setUp(self):
        self.now = datetime.now()
        self.super_admin = SuperAdminUserFactory()
        self.super_admin.save()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.brand = self.brand
        self.super_admin.brand = self.brand
        self.super_admin.save()

        self.agent = Agent(
            msisdn='01021469732',
            wallet_provider=self.super_admin,
        )
        self.agent.save()
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
        self.callwalletsmoderator = CallWalletsModerator.objects.create(
            user_created=self.root,
            disbursement=True,
            change_profile=False,
            set_pin=False,
            user_inquiry=True,
            balance_inquiry=False,
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

        self.super_admin.save()
        self.maker_user = MakerUser(
            id=14,
            username='test_maker_user',
            email='t@mk.com',
            root=self.root,
            user_type=1,
        )
        self.maker_user.save()
        self.budget = Budget(disburser=self.root, current_balance=1500)
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

        # create doc, doc_review, DisbursementDocData, file category
        self.file_category = FileCategory.objects.create(user_created=self.root)

    def test_BankWalletsAndCardsSheetProcessor(self):
        if not os.path.exists(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
        ):
            os.makedirs(
                f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
            )

        df = pd.DataFrame(
            {
                'mobile number': ['+201221409281', str('+001251409281'), '1211409281'],
                'amount': ['55', '50', '60'],
                'full name': ["test", 'test', 'test'],
                'issuer': ['Orange', 'Orange', 'Orange'],
            }
        )
        with pd.ExcelWriter(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/bank_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
        ) as writer:
            df.to_excel(writer, sheet_name='sheet1', index=False)

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=self.file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
            file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/bank_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls',
        )
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()
        self.assertTrue(BankWalletsAndCardsSheetProcessor.run(self.doc.id))

    def test_BankWalletsAndCardsSheetProcessor_with_comment(self):

        if not os.path.exists(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
        ):
            os.makedirs(
                f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
            )

        df = pd.DataFrame(
            {
                'mobile number': ['+201221409281', str('+001251409281'), '1211409281'],
                'amount': ['55', '50', '60'],
                'full name': ["test", 'test', 'test'],
                'issuer': ['Orange', 'Orange', 'Orange'],
                'comment1': ['comment', 'comment', 'comment'],
                'comment2': ['comment', 'comment', 'comment'],
            }
        )
        with pd.ExcelWriter(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/bank_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
        ) as writer:
            df.to_excel(writer, sheet_name='sheet1', index=False)

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=self.file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
            file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/bank_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls',
        )
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()
        self.assertTrue(BankWalletsAndCardsSheetProcessor.run(self.doc.id))

    def test_BankWalletsAndCardsSheetProcessor_bankcard(self):

        if not os.path.exists(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
        ):
            os.makedirs(
                f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
            )

        df = pd.DataFrame(
            {
                'account number / IBAN': ['21499268241871773200'],
                'amount': ['55'],
                'full name': ["Timothy Gonzalez Heather"],
                'bank swift code': ['SAIB'],
                'transaction type': ['cash_transfer'],
            }
        )
        with pd.ExcelWriter(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/bank_cards_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
        ) as writer:
            df.to_excel(writer, sheet_name='sheet1', index=False)

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=self.file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
            file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/bank_cards_sample_file_{self.maker_user.username}_72RYZL00Y.xls',
        )
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.doc.type_of = AbstractBaseDocType.BANK_CARDS
        self.doc.save()
        self.assertTrue(BankWalletsAndCardsSheetProcessor.run(self.doc.id))

    def test_BankWalletsAndCardsSheetProcessor_bankcard_with_comment(self):

        if not os.path.exists(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
        ):
            os.makedirs(
                f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
            )

        df = pd.DataFrame(
            {
                'account number / IBAN': ['21499268241871773200'],
                'amount': ['55'],
                'full name': ["Timothy Gonzalez Heather"],
                'bank swift code': ['SAIB'],
                'transaction type': ['cash_transfer'],
                'comment1': [
                    'comment',
                ],
                'comment2': [
                    'comment',
                ],
            }
        )
        with pd.ExcelWriter(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/bank_cards_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
        ) as writer:
            df.to_excel(writer, sheet_name='sheet1', index=False)

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=self.file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
            file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/bank_cards_sample_file_{self.maker_user.username}_72RYZL00Y.xls',
        )
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.doc.type_of = AbstractBaseDocType.BANK_CARDS
        self.doc.save()
        self.assertTrue(BankWalletsAndCardsSheetProcessor.run(self.doc.id))

    def test_BankWalletsAndCardsSheetProcessor_with_end_with_failure_sheet_details(
        self,
    ):

        if not os.path.exists(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
        ):
            os.makedirs(
                f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
            )

        df = pd.DataFrame(
            {
                'mobile number': ['+201221409281', '', '`1211409281', '0585285566'],
                'amount': ['55', '50', '60', ''],
                'full name': ["test", 'test', 'test', ''],
                'issuer': ['Orange', 'Orange', 'Orange', ''],
            }
        )
        with pd.ExcelWriter(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/banks_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
        ) as writer:
            df.to_excel(writer, sheet_name='sheet1', index=False)

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=self.file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
            file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/banks_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls',
        )
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.doc.id))

    def test_BankWalletsAndCardsSheetProcessor_bankcard_with_end_with_failure_sheet_details(
        self,
    ):

        if not os.path.exists(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
        ):
            os.makedirs(
                f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
            )

        df = pd.DataFrame(
            {
                'account number / IBAN': [
                    'EG000982865194179876596014703',
                    'EG000982865194179876596014703',
                    '84841515815158545',
                    'dkjkllklkkl',
                    '',
                ],
                'amount': ['55', '55', '', '58', '55'],
                'full name': ["Timothy Gonzalez Heather", 'test', '', 'test', 'test1'],
                'bank swift code': ['858', 'test', '', 'test', 'fake'],
                'transaction type': [
                    'cash_transfer',
                    'test',
                    '',
                    'cash_transfer',
                    'fake',
                ],
            }
        )
        with pd.ExcelWriter(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/bank_cards_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
        ) as writer:
            df.to_excel(writer, sheet_name='sheet1', index=False)

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=self.file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
            file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/bank_cards_sample_file_{self.maker_user.username}_72RYZL00Y.xls',
        )
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.doc.type_of = AbstractBaseDocType.BANK_CARDS
        self.doc.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.doc.id))

    def test_BankWalletsAndCardsSheetProcessor_with_end_with_failure(self):
        if not os.path.exists(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
        ):
            os.makedirs(
                f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
            )

        df = pd.DataFrame(
            {
                'mobile number': ['+201221409281', str('+001251409281'), '`1211409281'],
                'amount': ['55', '50', '60'],
                'full name': ["test", 'test', 'test'],
                'issuer': ['Orange', 'Orange', 'Orange'],
            }
        )
        with pd.ExcelWriter(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/bank_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
        ) as writer:
            df.to_excel(writer, sheet_name='sheet1', index=False)

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=self.file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
            file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/bank_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls',
        )
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()
        self.callwalletsmoderator.disbursement = False
        self.callwalletsmoderator.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.doc.id))

    def test_BankWalletsAndCardsSheetProcessor_amount_exceed_budget(self):

        if not os.path.exists(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
        ):
            os.makedirs(
                f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
            )

        df = pd.DataFrame(
            {
                'mobile number': ['+201221409281', str('+001251409281'), '1211409281'],
                'amount': ['55', '50', '60'],
                'full name': ["test", 'test', 'test'],
                'issuer': ['Orange', 'Orange', 'Orange'],
            }
        )
        with pd.ExcelWriter(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/bank_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
        ) as writer:
            df.to_excel(writer, sheet_name='sheet1', index=False)

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=self.file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
            file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/bank_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls',
        )
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()
        self.budget.current_balance = 150
        self.budget.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.doc.id))

    def test_BankWalletsAndCardsSheetProcessor_Duplicate_mobile_number(self):
        if not os.path.exists(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
        ):
            os.makedirs(
                f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
            )

        df = pd.DataFrame(
            {
                'mobile number': [
                    '+201221409281',
                    str('+201221409281'),
                    '+201221409281',
                ],
                'amount': ['55', '50', '60'],
                'full name': ["test", 'test', 'test'],
                'issuer': ['Orange', 'Orange', 'Orange'],
            }
        )
        with pd.ExcelWriter(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/bank_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
        ) as writer:
            df.to_excel(writer, sheet_name='sheet1', index=False)

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=self.file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
            file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/bank_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls',
        )
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()
        self.budget.current_balance = 150
        self.budget.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.doc.id))

    def test_BankWalletsAndCardsSheetProcessor_without_name(self):
        if not os.path.exists(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
        ):
            os.makedirs(
                f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
            )

        df = pd.DataFrame(
            {
                'mobile number': ['+201221409281', str('+001251409281'), '1211409281'],
                'amount': ['55', '50', '60'],
                'full name': ["test", 'test', ''],
                'issuer': ['Orange', 'Orange', 'Orange'],
            }
        )
        with pd.ExcelWriter(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/bank_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
        ) as writer:
            df.to_excel(writer, sheet_name='sheet1', index=False)

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=self.file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
            file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/bank_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls',
        )
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.doc.id))

    def test_BankWalletsAndCardsSheetProcessor_bankcard_with_invalid_amount(self):

        if not os.path.exists(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
        ):
            os.makedirs(
                f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
            )

        df = pd.DataFrame(
            {
                'account number / IBAN': ['21499268241871773200'],
                'amount': ['ddd'],
                'full name': ["Timothy Gonzalez Heather"],
                'bank swift code': ['SAIB'],
                'transaction type': ['cash_transfer'],
            }
        )
        with pd.ExcelWriter(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/bank_cards_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
        ) as writer:
            df.to_excel(writer, sheet_name='sheet1', index=False)

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=self.file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
            file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/bank_cards_sample_file_{self.maker_user.username}_72RYZL00Y.xls',
        )
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.doc.type_of = AbstractBaseDocType.BANK_CARDS
        self.doc.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.doc.id))

    # def test_BankWalletsAndCardsSheetProcessor_with_error(self):
    #     if not os.path.exists(f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'):
    #         os.makedirs(f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}')

    #     df=pd.DataFrame(
    #         {
    #             'mobile number':['+201221409281', str('+001251409281'),'1211409281'],
    #             'amount':['55','50', ],
    #             'full name':["test", 'test', ],
    #             'issuer':['Orange', 'Orange', 'Orange']
    #         }
    #     )
    #     with pd.ExcelWriter(f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/banks_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls') as writer:
    #         df.to_excel(writer, sheet_name='sheet1', index=False)

    #     self.doc = Doc.objects.create(
    #             owner=self.maker_user,
    #             file_category=self.file_category,
    #             is_disbursed=True,
    #             can_be_disbursed=True,
    #             is_processed=True,
    #             file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/banks_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
    #     )
    #     disb_doc_data = DisbursementDocData.objects.create(
    #         doc=self.doc,
    #         txn_status = "200",
    #         has_callback = True,
    #         doc_status = "5"
    #     )
    #     self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
    #     self.doc.save()
    #     self.assertTrue(
    #         BankWalletsAndCardsSheetProcessor.run(
    #                 self.doc.id
    #         )
    #     )

    # def test_BankWalletsAndCardsSheetProcessor_bankcard_with_error(self):

    #     if not os.path.exists(f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'):
    #         os.makedirs(f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}')

    #     df=pd.DataFrame(
    #         {
    #             'account number / IBAN':['21499268241871773200'],
    #             'amount':['255', '55'],
    #             'full name':["Timothy Gonzalez Heather"],
    #             'bank swift code':['SAIB'],
    #             'transaction type':['cash_transfer'],
    #             'comment1':['comment',],
    #             'comment2': ['comment',]
    #         }
    #     )
    #     with pd.ExcelWriter(f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/bank_cards_sample_file_{self.maker_user.username}_72RYZL00Y.xls') as writer:
    #         df.to_excel(writer, sheet_name='sheet1', index=False)

    #     self.doc = Doc.objects.create(
    #             owner=self.maker_user,
    #             file_category=self.file_category,
    #             is_disbursed=True,
    #             can_be_disbursed=True,
    #             is_processed=True,
    #             file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/bank_cards_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
    #     )
    #     disb_doc_data = DisbursementDocData.objects.create(
    #         doc=self.doc,
    #         txn_status = "200",
    #         has_callback = True,
    #         doc_status = "5"
    #     )
    #     self.doc.type_of = AbstractBaseDocType.BANK_CARDS
    #     self.doc.save()
    #     self.assertFalse(
    #         BankWalletsAndCardsSheetProcessor.run(
    #                 self.doc.id
    #         )
    #     )

    def test_BankWalletsAndCardsSheetProcessor_with_exced_max_amount_can_be_disbursed(
        self,
    ):
        if not os.path.exists(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
        ):
            os.makedirs(
                f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
            )
        self.level.max_amount_can_be_disbursed = 10
        self.level.save()
        df = pd.DataFrame(
            {
                'mobile number': ['+201221409281', str('+001251409281'), '1211409281'],
                'amount': ['55', '50', '60'],
                'full name': ["test", 'test', 'test'],
                'issuer': ['Orange', 'Orange', 'Orange'],
            }
        )
        with pd.ExcelWriter(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/bank_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
        ) as writer:
            df.to_excel(writer, sheet_name='sheet1', index=False)

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=self.file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
            file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/bank_wallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls',
        )
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.doc.id))


class MockResponse:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = True

    def json(self):
        return {'TXNSTATUS': '200'}


class MockResponse_with_error:
    def __init__(self):
        self.status_code = 200
        self.text = 'test'
        self.ok = True

    def json(self):
        return {'TXNSTATUS': '201', 'MESSAGE': 'error'}


class TestEWalletsSheetProcessor(TestCase):
    def setUp(self):
        self.now = datetime.now()
        self.super_admin = SuperAdminUserFactory()
        self.super_admin.wallet_fees_profile = 0
        self.super_admin.save()
        self.super_admin.save()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.brand = self.brand
        self.super_admin.brand = self.brand
        self.super_admin.save()

        self.agent = Agent(
            msisdn='01021469732',
            wallet_provider=self.super_admin,
        )
        self.agent.save()
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
        self.callwalletsmoderator = CallWalletsModerator.objects.create(
            user_created=self.root,
            disbursement=True,
            change_profile=True,
            set_pin=False,
            user_inquiry=True,
            balance_inquiry=False,
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

        self.super_admin.save()
        self.maker_user = MakerUser(
            id=14,
            username='test_maker_user',
            email='t@mk.com',
            root=self.root,
            user_type=1,
        )
        self.maker_user.save()
        self.budget = Budget(disburser=self.root, current_balance=1500)
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

        # create doc, doc_review, DisbursementDocData, file category
        self.file_category = FileCategory.objects.create(
            unique_field='A-1',
            amount_field='B-1',
            issuer_field='C-1',
            user_created=self.root,
        )
        self.entity_setups = EntitySetup.objects.create(
            agents_setup=True,
            fees_setup=True,
            is_normal_flow=True,
            entity=self.root,
            user=self.super_admin,
        )

    @patch("requests.post", return_value=MockResponse())
    def test_EWalletsSheetProcessor_with_MockResponse(self, mocked):
        if not os.path.exists(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
        ):
            os.makedirs(
                f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
            )
        df = pd.DataFrame(
            {
                'mobile number': ['01010101010', '1251409281', '201211409281'],
                'amount': ['55', '50', '60'],
                'issuer': ["vodafone", 'etisalat', 'aman'],
                'comment 1': ['comment', 'comment', 'comment'],
                'comment 2': ['comment', 'comment', 'comment'],
            }
        )
        with pd.ExcelWriter(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/Ewallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
        ) as writer:
            df.to_excel(writer, sheet_name='sheet1', index=False)

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=self.file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
            file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/Ewallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls',
        )
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()
        self.assertTrue(EWalletsSheetProcessor.run(self.doc.id))

    @patch("requests.post", return_value=MockResponse())
    def test_EWalletsSheetProcessor_not_normal_sheet_specs(self, mocked):
        self.entity_setups.is_normal_flow = False
        self.entity_setups.save()
        if not os.path.exists(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
        ):
            os.makedirs(
                f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
            )
        df = pd.DataFrame(
            {
                'mobile number': ['01010101010', '1251409281', '201211409281'],
                'amount': ['55', '50', '60'],
                'issuer': ["vodafone", 'etisalat', 'aman'],
                'comment 1': ['comment', 'comment', 'comment'],
                'comment 2': ['comment', 'comment', 'comment'],
            }
        )
        with pd.ExcelWriter(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/Ewallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
        ) as writer:
            df.to_excel(writer, sheet_name='sheet1', index=False)

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=self.file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
            file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/Ewallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls',
        )
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()
        self.assertTrue(EWalletsSheetProcessor.run(self.doc.id))

    @patch("requests.post", return_value=MockResponse_with_error())
    def test_EWalletsSheetProcessor(self, mocked):
        if not os.path.exists(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
        ):
            os.makedirs(
                f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
            )
        df = pd.DataFrame(
            {
                'mobile number': ['01010101010', '1251409281', '201211409281'],
                'amount': ['55', '50', '60'],
                'issuer': ["vodafone", 'etisalat', 'aman'],
                'comment 1': ['comment', 'comment', 'comment'],
                'comment 2': ['comment', 'comment', 'comment'],
            }
        )
        with pd.ExcelWriter(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/Ewallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
        ) as writer:
            df.to_excel(writer, sheet_name='sheet1', index=False)

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=self.file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
            file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/Ewallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls',
        )
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()
        self.assertFalse(EWalletsSheetProcessor.run(self.doc.id))

    def test_EWalletsSheetProcessor_with_error_in_sheet_details(self):
        self.entity_setups.is_normal_flow = False
        self.entity_setups.save()
        if not os.path.exists(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
        ):
            os.makedirs(
                f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
            )
        df = pd.DataFrame(
            {
                'mobile number': [
                    '01010101010',
                    '01010101010',
                    '201211409281',
                    '',
                    '`444',
                ],
                'amount': ['55', '50', '60', '', 'test'],
                'issuer': ["vodafone", 'etisalat', 'aman', '', 'test'],
                'comment 1': ['comment', 'comment', 'comment', '', ''],
                'comment 2': ['comment', 'comment', 'comment', '', ''],
            }
        )
        with pd.ExcelWriter(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/Ewallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
        ) as writer:
            df.to_excel(writer, sheet_name='sheet1', index=False)

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=self.file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
            file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/Ewallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls',
        )
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()
        self.assertFalse(EWalletsSheetProcessor.run(self.doc.id))

    def test_EWalletsSheetProcessor_with_error_in_sheet_details_And_sheet_is_normal_flow(
        self,
    ):

        if not os.path.exists(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
        ):
            os.makedirs(
                f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}'
            )
        df = pd.DataFrame(
            {
                'mobile number': [
                    '01010101010',
                    '01010101010',
                    '201211409281',
                    '',
                    '`444',
                ],
                'amount': ['55', '50', '60', '', 'test'],
                'issuer': ["vodafone", 'etisalat', 'aman', '', 'test'],
                'comment 1': ['comment', 'comment', 'comment', '', ''],
                'comment 2': ['comment', 'comment', 'comment', '', ''],
            }
        )
        with pd.ExcelWriter(
            f'/app/mediafiles/media/documents/files_uploaded/{self.now.year}/{self.now.day}/Ewallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls'
        ) as writer:
            df.to_excel(writer, sheet_name='sheet1', index=False)

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=self.file_category,
            is_disbursed=True,
            can_be_disbursed=True,
            is_processed=True,
            file=f'documents/files_uploaded/{self.now.year}/{self.now.day}/Ewallets_sample_file_{self.maker_user.username}_72RYZL00Y.xls',
        )
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )
        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()
        self.assertFalse(EWalletsSheetProcessor.run(self.doc.id))


class TestExportClientsTransactionsMonthlyReportTask(TestCase):
    def setUp(self):
        super().setUp()
        # create root
        self.super_admin = SuperAdminUserFactory()
        self.super_admin2 = SuperAdminUserFactory()
        self.super_admin2.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users',
                codename='vodafone_facilitator_accept_vodafone_onboarding',
            )
        )

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
        self.super_admin.user_permissions.add(
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
        Disbursementdata_success_vodafone = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01010801010',
            issuer='vodafone',
            is_disbursed=True,
            disbursed_date=datetime.now(),
        )
        Disbursementdata_pending_vodafone = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01010171011',
            issuer='vodafone',
            disbursed_date=datetime.now(),
        )
        Disbursementdata_failed_vodafone = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01010141012',
            issuer='vodafone',
            is_disbursed=False,
            reason='test',
            disbursed_date=datetime.now(),
        )
        Disbursementdata_success_etisalat = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01110101010',
            issuer='etisalat',
            is_disbursed=True,
            disbursed_date=datetime.now(),
        )
        Disbursementdata_pending_etisalat = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01110108011',
            issuer='etisalat',
            disbursed_date=datetime.now(),
        )
        Disbursementdata_failed_etisalat = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01110103012',
            issuer='etisalat',
            is_disbursed=False,
            reason='test',
            disbursed_date=datetime.now(),
        )
        Disbursementdata_success_aman = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01010105010',
            issuer='aman',
            is_disbursed=True,
            disbursed_date=datetime.now(),
        )
        Disbursementdata_pending_aman = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01010108011',
            issuer='aman',
            disbursed_date=datetime.now(),
        )
        Disbursementdata_failed_aman = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01010107012',
            issuer='aman',
            is_disbursed=False,
            reason='test',
            disbursed_date=datetime.now(),
        )
        self.instanttransaction_Orange_success = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='S',
        )
        self.instanttransaction_Orange_failed = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='F',
        )
        self.instanttransaction_Orange_pending = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='P',
        )
        self.instanttransaction_BankWallet_success = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.BANK_WALLET,
            disbursed_date=datetime.now(),
            status='S',
        )
        self.instanttransaction_BankWallet_failed = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.BANK_WALLET,
            disbursed_date=datetime.now(),
            status='F',
        )
        self.instanttransaction_BankWallet_pending = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.BANK_WALLET,
            disbursed_date=datetime.now(),
            status='P',
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
            disbursed_date=datetime.now(),
        )
        self.banktransaction_failed = BankTransaction.objects.create(
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
            status='F',
            comment1="",
            comment2="",
            disbursed_date=datetime.now(),
        )
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
            disbursed_date=datetime.now(),
        )

    def test_ExportClientsTransactionsMonthlyReportTask_Success(self):

        self.assertTrue(
            ExportClientsTransactionsMonthlyReportTask.run(
                user_id=self.super_admin.id,
                start_date=datetime.today().strftime('%Y-%m-%d'),
                end_date=datetime.today().strftime('%Y-%m-%d'),
                status='success',
                super_admins_ids=[self.super_admin.id],
            )
        )

    def test_ExportClientsTransactionsMonthlyReportTask_Failed(self):
        self.assertTrue(
            ExportClientsTransactionsMonthlyReportTask.run(
                user_id=self.super_admin.id,
                start_date=datetime.today().strftime('%Y-%m-%d'),
                end_date=datetime.today().strftime('%Y-%m-%d'),
                status='failed',
                super_admins_ids=[self.super_admin.id],
            )
        )

    def test_ExportClientsTransactionsMonthlyReportTask_all(self):
        self.assertTrue(
            ExportClientsTransactionsMonthlyReportTask.run(
                user_id=self.super_admin.id,
                start_date=datetime.today().strftime('%Y-%m-%d'),
                end_date=datetime.today().strftime('%Y-%m-%d'),
                status='all',
                super_admins_ids=[self.super_admin.id],
            )
        )

    # def test_ExportClientsTransactionsMonthlyReportTask_Invoices(self):
    #     self.assertTrue(
    #         ExportClientsTransactionsMonthlyReportTask.run(
    #             user_id=self.super_admin.id,
    #             start_date=datetime.today().strftime('%Y-%m-%d'),
    #             end_date=datetime.today().strftime('%Y-%m-%d'),
    #             status='invoices',
    #             super_admins_ids=[self.super_admin.id],
    #             automatic_fire=True
    #         )
    #     )


class TestExportPortalRootOrDashboardUserTransactionsEwallets(TestCase):
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
        self.super_admin.user_permissions.add(
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

        self.instanttransaction_Orange_success = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='S',
        )
        self.instanttransaction_Orange_failed = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='F',
        )
        self.instanttransaction_Orange_pending = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='P',
        )
        self.instanttransaction_BankWallet_success = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.BANK_WALLET,
            disbursed_date=datetime.now(),
            status='S',
        )
        self.instanttransaction_BankWallet_failed = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.BANK_WALLET,
            disbursed_date=datetime.now(),
            status='F',
        )
        self.instanttransaction_BankWallet_pending = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.BANK_WALLET,
            disbursed_date=datetime.now(),
            status='P',
        )

    def test_ExportPortalRootOrDashboardUserTransactionsEwallets_root(self):
        self.assertIsNone(
            ExportPortalRootOrDashboardUserTransactionsEwallets.run(
                user_id=self.root.id,
                start_date=datetime.today().strftime('%Y-%m-%d'),
                end_date=datetime.today().strftime('%Y-%m-%d'),
            )
        )

    def test_ExportPortalRootOrDashboardUserTransactionsEwallets_checker(self):
        self.assertIsNone(
            ExportPortalRootOrDashboardUserTransactionsEwallets.run(
                user_id=self.checker_user.id,
                start_date=datetime.today().strftime('%Y-%m-%d'),
                end_date=datetime.today().strftime('%Y-%m-%d'),
            )
        )

    def test_ExportPortalRootOrDashboardUserTransactionsEwallets_maker(self):
        self.assertIsNone(
            ExportPortalRootOrDashboardUserTransactionsEwallets.run(
                user_id=self.maker_user.id,
                start_date=datetime.today().strftime('%Y-%m-%d'),
                end_date=datetime.today().strftime('%Y-%m-%d'),
            )
        )


class TestExportPortalRootOrDashboardUserTransactionsBanks(TestCase):
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
        self.super_admin.user_permissions.add(
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
            disbursed_date=datetime.now(),
        )
        self.banktransaction_failed = BankTransaction.objects.create(
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
            status='F',
            comment1="",
            comment2="",
            disbursed_date=datetime.now(),
        )
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
            disbursed_date=datetime.now(),
        )

    def test_ExportPortalRootOrDashboardUserTransactionsBanks_root(self):
        self.assertIsNone(
            ExportPortalRootOrDashboardUserTransactionsBanks.run(
                user_id=self.root.id,
                start_date=datetime.today().strftime('%Y-%m-%d'),
                end_date=datetime.today().strftime('%Y-%m-%d'),
            )
        )

    def test_ExportPortalRootOrDashboardUserTransactionsBanks_checker(self):
        self.assertIsNone(
            ExportPortalRootOrDashboardUserTransactionsBanks.run(
                user_id=self.checker_user.id,
                start_date=datetime.today().strftime('%Y-%m-%d'),
                end_date=datetime.today().strftime('%Y-%m-%d'),
            )
        )

    def test_ExportPortalRootOrDashboardUserTransactionsBanks_maker(self):
        self.assertIsNone(
            ExportPortalRootOrDashboardUserTransactionsBanks.run(
                user_id=self.maker_user.id,
                start_date=datetime.today().strftime('%Y-%m-%d'),
                end_date=datetime.today().strftime('%Y-%m-%d'),
            )
        )


class TestExportPortalRootTransactionsEwallet(TestCase):
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
        self.super_admin.user_permissions.add(
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
        Disbursementdata_success_vodafone = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01010801010',
            issuer='vodafone',
            is_disbursed=True,
            disbursed_date=datetime.now(),
        )
        Disbursementdata_pending_vodafone = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01010171011',
            issuer='vodafone',
            disbursed_date=datetime.now(),
        )
        Disbursementdata_failed_vodafone = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01010141012',
            issuer='vodafone',
            is_disbursed=False,
            reason='test',
            disbursed_date=datetime.now(),
        )
        Disbursementdata_success_etisalat = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01110101010',
            issuer='etisalat',
            is_disbursed=True,
            disbursed_date=datetime.now(),
        )
        Disbursementdata_pending_etisalat = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01110108011',
            issuer='etisalat',
            disbursed_date=datetime.now(),
        )
        Disbursementdata_failed_etisalat = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01110103012',
            issuer='etisalat',
            is_disbursed=False,
            reason='test',
            disbursed_date=datetime.now(),
        )
        Disbursementdata_success_aman = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01010105010',
            issuer='aman',
            is_disbursed=True,
            disbursed_date=datetime.now(),
        )
        Disbursementdata_pending_aman = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01010108011',
            issuer='aman',
            disbursed_date=datetime.now(),
        )
        Disbursementdata_failed_aman = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01010107012',
            issuer='aman',
            is_disbursed=False,
            reason='test',
            disbursed_date=datetime.now(),
        )

    def test_ExportPortalRootTransactionsEwallet_root(self):
        self.assertIsNone(
            ExportPortalRootTransactionsEwallet.run(
                user_id=self.root.id,
                start_date=datetime.today().strftime('%Y-%m-%d'),
                end_date=datetime.today().strftime('%Y-%m-%d'),
            )
        )

    def test_ExportPortalRootTransactionsEwallet_checker(self):
        self.assertIsNone(
            ExportPortalRootTransactionsEwallet.run(
                user_id=self.checker_user.id,
                start_date=datetime.today().strftime('%Y-%m-%d'),
                end_date=datetime.today().strftime('%Y-%m-%d'),
            )
        )

    def test_ExportPortalRootTransactionsEwallet_maker(self):
        self.assertIsNone(
            ExportPortalRootTransactionsEwallet.run(
                user_id=self.maker_user.id,
                start_date=datetime.today().strftime('%Y-%m-%d'),
                end_date=datetime.today().strftime('%Y-%m-%d'),
            )
        )


class Testgenerate_failed_disbursed_data(TestCase):
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
        self.super_admin.user_permissions.add(
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

        Disbursementdata_failed_vodafone = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01010141012',
            issuer='vodafone',
            is_disbursed=False,
            reason='test',
            disbursed_date=datetime.now(),
        )
        Disbursementdata_failed_etisalat = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01110103012',
            issuer='etisalat',
            is_disbursed=False,
            reason='test',
            disbursed_date=datetime.now(),
        )
        Disbursementdata_failed_aman = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01010107012',
            issuer='aman',
            is_disbursed=False,
            reason='test',
            disbursed_date=datetime.now(),
        )

    def test_generate_failed_disbursed_data(self):
        self.assertIsNone(
            generate_failed_disbursed_data(doc_id=self.doc.id, user_id=self.root.id)
        )


class Testgenerate_success_disbursed_data(TestCase):
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
        self.super_admin.user_permissions.add(
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

        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()

        self.instanttransaction_Orange_success = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now(),
            status='S',
        )
        self.instanttransaction_BankWallet_success = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.BANK_WALLET,
            disbursed_date=datetime.now(),
            status='S',
        )

    def test_generate_success_disbursed_data(self):
        self.assertIsNone(
            generate_success_disbursed_data(doc_id=self.doc.id, user_id=self.root.id)
        )


class Testgenerate_all_disbursed_data(TestCase):
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
        self.super_admin.user_permissions.add(
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
            disbursed_date=datetime.now(),
        )
        self.banktransaction_failed = BankTransaction.objects.create(
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
            status='F',
            comment1="",
            comment2="",
            disbursed_date=datetime.now(),
        )
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
            disbursed_date=datetime.now(),
        )

    def test_generate_all_disbursed_data(self):
        self.assertIsNone(
            generate_all_disbursed_data(doc_id=self.doc.id, user_id=self.root.id)
        )


class Test_notify_checkers(TestCase):
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
        self.level = Levels(
            max_amount_can_be_disbursed=1200, created=self.root, level_of_authority=1200
        )
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

        self.doc.type_of = AbstractBaseDocType.BANK_CARDS
        self.doc.save()

    def test_notify_checkers(self):
        self.assertIsNone(notify_checkers(doc_id=self.doc.id, level=1200))
        self.assertIsNone(notify_checkers(doc_id=self.doc.id, level=120))


class Test_notify_disbursers(TestCase):
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
        self.level = Levels(
            max_amount_can_be_disbursed=1200, created=self.root, level_of_authority=1200
        )
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

        self.doc.type_of = AbstractBaseDocType.BANK_CARDS
        self.doc.save()

    def test_notify_disbursers(self):
        self.assertIsNone(notify_disbursers(doc_id=self.doc.id, min_level=1300))
        self.assertIsNone(notify_disbursers(doc_id=self.doc.id, min_level=120))


class Test_doc_review_maker_mail(TestCase):
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
        self.level = Levels(
            max_amount_can_be_disbursed=1200, created=self.root, level_of_authority=1200
        )
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
        self.doc_review = DocReview.objects.create(
            is_ok=True,
            doc=self.doc,
            user_created=self.checker_user,
        )
        disb_data_doc = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )

        self.doc.type_of = AbstractBaseDocType.BANK_CARDS
        self.doc.save()

    def test_doc_review_maker_mail(self):
        self.assertIsNone(
            doc_review_maker_mail(
                doc_id=self.doc.id,
                review_id=self.doc_review.id,
            )
        )

    def test_doc_review_maker_mail_with_doc_wallet_and_doc_review_false(self):
        self.doc.type_of = AbstractBaseDocType.E_WALLETS
        self.doc.save()
        self.doc_review.is_ok = False
        self.doc_review.save()
        self.assertIsNone(
            doc_review_maker_mail(
                doc_id=self.doc.id,
                review_id=self.doc_review.id,
            )
        )


class Testnotify_maker_(TestCase):
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
        self.level = Levels(
            max_amount_can_be_disbursed=1200, created=self.root, level_of_authority=1200
        )
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
            file='test',
        )
        self.doc_review = DocReview.objects.create(
            is_ok=True,
            doc=self.doc,
            user_created=self.checker_user,
        )
        disb_data_doc = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )

        self.doc.type_of = AbstractBaseDocType.BANK_CARDS
        self.doc.save()

    def test_notify_maker_is_processed_equal_false(self):
        self.doc.is_processed = False
        self.assertIsNone(notify_maker(doc=self.doc, download_url='test'))

    def test_notify_maker_(self):
        self.assertIsNone(notify_maker(doc=self.doc, download_url='test'))


class Testcreate_recuring_docs(TestCase):
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
        self.level = Levels(
            max_amount_can_be_disbursed=1200, created=self.root, level_of_authority=1200
        )
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
            file='test',
            is_recuring=True,
            recuring_period=2,
            recuring_latest_date=datetime.now() - timedelta(days=2),
        )
        self.doc_review = DocReview.objects.create(
            is_ok=True,
            doc=self.doc,
            user_created=self.checker_user,
        )
        disb_data_doc = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )

    def test_create_recuring_docs_with_doc_is_e_wallet(self):
        self.doc.type_of = AbstractBaseDocType.E_WALLETS
        self.doc.save()
        Disbursementdata_failed_vodafone = DisbursementData.objects.create(
            doc=self.doc,
            amount=100,
            msisdn='01010141012',
            issuer='vodafone',
            is_disbursed=False,
            reason='test',
            disbursed_date=datetime.now() - timedelta(days=2),
        )
        self.assertIsNone(create_recuring_docs())

    def test_create_recuring_docs_with_doc_is_bank_wallet(self):
        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()
        self.instanttransaction_Orange_success = InstantTransaction.objects.create(
            document=self.doc,
            from_user=self.checker_user,
            issuer_type=InstantTransaction.ORANGE,
            disbursed_date=datetime.now() - timedelta(days=2),
            status='S',
        )
        self.assertIsNone(create_recuring_docs())

    def test_create_recuring_docs_with_doc_is_bank_card(self):
        self.doc.type_of = AbstractBaseDocType.BANK_CARDS
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
            status='p',
            comment1="",
            comment2="",
            disbursed_date=datetime.now() - timedelta(days=2),
        )
        self.assertIsNone(create_recuring_docs())


class Testgenerate_vf_daily_report(TestCase):
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
        self.root.save()
        self.checker_user.save()
        self.level = Levels(
            max_amount_can_be_disbursed=1200, created=self.root, level_of_authority=1200
        )
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
                content_type__app_label='users',
                codename='vodafone_facilitator_accept_vodafone_onboarding',
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
            file='test',
        )
        self.doc_review = DocReview.objects.create(
            is_ok=True,
            doc=self.doc,
            user_created=self.checker_user,
        )
        disb_data_doc = DisbursementDocData.objects.create(
            doc=self.doc, txn_status="200", has_callback=True, doc_status="5"
        )

        self.doc.type_of = AbstractBaseDocType.BANK_CARDS
        self.doc.save()

    def test_generate_vf_daily_report(self):

        self.assertIsNone(generate_vf_daily_report())
