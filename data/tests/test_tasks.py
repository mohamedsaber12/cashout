# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile

from users.tests.factories import (
    SuperAdminUserFactory, AdminUserFactory, VMTDataFactory
)
from users.models import (
    Client as ClientModel, Brand, EntitySetup, CheckerUser, Levels,
    MakerUser, Setup
)
from data.models import Doc, FileCategory, DocReview
from utilities.models import Budget, FeeSetup, CallWalletsModerator, AbstractBaseDocType
from disbursement.models import DisbursementDocData

from data.tasks import (
    EWalletsSheetProcessor, BankWalletsAndCardsSheetProcessor
)


class EWalletsSheetProcessorTests(TestCase):

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
            max_amount_can_be_disbursed=3000,
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
            email='t@mk.com',
            root=self.root,
            user_type=1
        )
        self.maker_user.save()
        self.maker_user.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding')
        )
        self.budget = Budget(disburser=self.root, current_balance=15000)
        self.budget.save()
        fees_setup_vodafone = FeeSetup(budget_related=self.budget, issuer='vf',
                                       fee_type='p', percentage_value=2.25)
        fees_setup_vodafone.save()

        fees_setup_etisalat = FeeSetup(budget_related=self.budget, issuer='es',
                                       fee_type='p', percentage_value=2.25)
        fees_setup_etisalat.save()

        fees_setup_aman = FeeSetup(budget_related=self.budget, issuer='am',
                                    fee_type='p', percentage_value=2.25)
        fees_setup_aman.save()

        self.entity_setup = EntitySetup.objects.create(
            user=self.super_admin,
            entity=self.root,
            agents_setup=True,
            fees_setup=True,
            is_normal_flow=False
        )
        self.wallet_moderator = CallWalletsModerator.objects.create(
            user_created=self.root, disbursement=True, change_profile=False, set_pin=False,
            user_inquiry=False, balance_inquiry=False
        )

        # create doc, doc_review, DisbursementDocData, file category
        file_category = FileCategory.objects.create(
            user_created=self.root,
            name='salaries',
            unique_field= 'A-1',
            amount_field= 'B-1',
            issuer_field= 'C-1',
            no_of_reviews_required= 1
        )

        self.doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=file_category,
            file=SimpleUploadedFile(
                "e_wallet_sheet.csv",
                b"mobile number,amount,issuer\n"
                b"1265645842,34.03,vodafone\n"
                b"01006260411,476.86,etisalat\n"
                b"201045087208,88.33,vodafone\n"
                b"01263214158,174.53,aman"
            )
        )
        DisbursementDocData.objects.create(
            doc=self.doc
        )

    def test_e_wallets_sheet_processor(self):
        self.assertTrue(EWalletsSheetProcessor.run(self.doc.id))

    def test_e_wallets_sheet_processor_with_normal_flew(self):
        self.entity_setup.is_normal_flow = True
        self.entity_setup.save()
        self.assertFalse(EWalletsSheetProcessor.run(self.doc.id))

    def test_total_amount_less_than_max_amount_can_be_disbursed(self):
        self.level.max_amount_can_be_disbursed=30
        self.level.save()
        self.assertFalse(EWalletsSheetProcessor.run(self.doc.id))

    def test_has_not_sufficient_budget(self):
        self.budget.current_balance=150
        self.budget.save()
        self.assertFalse(EWalletsSheetProcessor.run(self.doc.id))

    def test_has_not_disbursement_permission(self):
        self.wallet_moderator.disbursement=False
        self.wallet_moderator.save()
        self.assertFalse(EWalletsSheetProcessor.run(self.doc.id))

    def test_valid_mobile_number_with_normal_flew(self):
        self.entity_setup.is_normal_flow = True
        self.entity_setup.save()
        self.doc.file=SimpleUploadedFile(
            "e_wallet_sheet.csv",
            b"mobile number,amount,issuer\n"
            b"5645842,34.03,vodafone\n"
            b"01006260411,476.86,etisalat\n"
            b"201045087208456,88.33,vodafone\n"
            b"01263214158,174.53,aman"
        )
        self.doc.save()
        self.assertFalse(EWalletsSheetProcessor.run(self.doc.id))

    def test_duplicate_mobile_number_with_normal_flew(self):
        self.entity_setup.is_normal_flow = True
        self.entity_setup.save()
        self.doc.file=SimpleUploadedFile(
            "e_wallet_sheet.csv",
            b"mobile number,amount,issuer\n"
            b"01263214158,34.03,vodafone\n"
            b"01006260411,476.86,etisalat\n"
            b"201045087208,88.33,vodafone\n"
            b"01263214158,174.53,aman"
        )
        self.doc.save()
        self.assertFalse(EWalletsSheetProcessor.run(self.doc.id))

    def test_valid_mobile_number_without_normal_flew(self):
        self.doc.file=SimpleUploadedFile(
            "e_wallet_sheet.csv",
            b"mobile number,amount,issuer\n"
            b"5645842,34.03,vodafone\n"
            b"01006260411,476.86,etisalat\n"
            b"201045087208456,88.33,vodafone\n"
            b"01263214158,174.53,aman"
        )
        self.doc.save()
        self.assertFalse(EWalletsSheetProcessor.run(self.doc.id))

    def test_duplicate_mobile_number_without_normal_flew(self):
        self.doc.file=SimpleUploadedFile(
            "e_wallet_sheet.csv",
            b"mobile number,amount,issuer\n"
            b"01263214158,34.03,vodafone\n"
            b"01006260411,476.86,etisalat\n"
            b"201045087208,88.33,vodafone\n"
            b"01263214158,174.53,aman"
        )
        self.doc.save()
        self.assertFalse(EWalletsSheetProcessor.run(self.doc.id))

    def test_invalid_issuer(self):
        self.doc.file=SimpleUploadedFile(
            "e_wallet_sheet.csv",
            b"mobile number,amount,issuer\n"
            b"01263214158,34.03,fake issuer\n"
            b"01006260411,476.86,etisalat\n"
            b"201045087208,88.33,vodafone\n"
            b"01263214158,174.53,aman"
        )
        self.doc.save()
        self.assertFalse(EWalletsSheetProcessor.run(self.doc.id))

    def test_doc_not_exist(self):
        self.assertFalse(EWalletsSheetProcessor.run('fake_doc_id866564566hjghv'))


class BankWalletsAndCardsSheetProcessorTests(TestCase):

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
            max_amount_can_be_disbursed=3000,
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
            email='t@mk.com',
            root=self.root,
            user_type=1
        )
        self.maker_user.save()
        self.maker_user.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding')
        )
        self.budget = Budget(disburser=self.root, current_balance=15000)
        self.budget.save()
        fees_setup_bank_wallet = FeeSetup(budget_related=self.budget, issuer='bw',
                                       fee_type='p', percentage_value=2.25)
        fees_setup_bank_wallet.save()

        fees_setup_orange = FeeSetup(budget_related=self.budget, issuer='og',
                                          fee_type='p', percentage_value=2.25)
        fees_setup_orange.save()

        fees_setup_bank_card = FeeSetup(budget_related=self.budget, issuer='bc',
                                       fee_type='p', percentage_value=2.25)
        fees_setup_bank_card.save()

        self.entity_setup = EntitySetup.objects.create(
            user=self.super_admin,
            entity=self.root,
            agents_setup=True,
            fees_setup=True,
            is_normal_flow=False
        )
        self.wallet_moderator = CallWalletsModerator.objects.create(
            user_created=self.root, disbursement=True, change_profile=False, set_pin=False,
            user_inquiry=False, balance_inquiry=False
        )

        # create doc, doc_review, DisbursementDocData, file category
        file_category = FileCategory.objects.create(
            user_created=self.root,
            name='salaries',
            unique_field= 'A-1',
            amount_field= 'B-1',
            issuer_field= 'C-1',
            no_of_reviews_required= 1
        )

        self.bank_wallet_doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=file_category,
            type_of=AbstractBaseDocType.BANK_WALLETS,
            file=SimpleUploadedFile(
                "bank_wallet_sheet.csv",
                b"mobile number,amount,full name,issuer\n"
                b"1265645842,34.03,test_name,orange\n"
                b"01006260411,476.86,test_name,bank_wallet\n"
                b"201045087208,88.33,test_name,bank_wallet\n"
                b"01263214158,174.53,test_name,orange"
            )
        )
        DisbursementDocData.objects.create(
            doc=self.bank_wallet_doc
        )
        self.bank_card_doc = Doc.objects.create(
            owner=self.maker_user,
            file_category=file_category,
            type_of=AbstractBaseDocType.BANK_CARDS,
            file=SimpleUploadedFile(
                "bank_card_sheet.csv",
                b"account number / IBAN,amount,full name,bank swift code,transaction type\n"
                b"7674893281142330164,34.03,test_name,SAIB,salary\n"
                b"EG889262908254516406224392104,476.86,test_name,FAIB,prepaid_card\n"
                b"09378928922645039,88.33,test_name,HSBC,credit_card"
            )
        )
        DisbursementDocData.objects.create(
           doc=self.bank_card_doc
        )

    def test_bank_wallets_sheet_processor(self):
        self.assertTrue(BankWalletsAndCardsSheetProcessor.run(self.bank_wallet_doc.id))

    def test_bank_cards_sheet_processor(self):
        self.assertTrue(BankWalletsAndCardsSheetProcessor.run(self.bank_card_doc.id))

    def test_valid_mobile_number_with_bank_wallet_sheet(self):
        self.bank_wallet_doc.file=SimpleUploadedFile(
            "bank_wallet_sheet.csv",
            b"mobile number,amount,full name,issuer\n"
            b"1265645842,34.03,test_name,orange\n"
            b"01000411,476.86,test_name,bank_wallet\n"
            b"20104508720854,88.33,test_name,bank_wallet\n"
            b"01263214158,174.53,test_name,orange"
        )
        self.bank_wallet_doc.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.bank_wallet_doc.id))

    def test_duplicate_mobile_number_witt_bank_wallet_sheet(self):
        self.bank_wallet_doc.file=SimpleUploadedFile(
            "bank_wallet_sheet.csv",
            b"mobile number,amount,full name,issuer\n"
            b"01263214158,34.03,test_name,orange\n"
            b"01006260411,476.86,test_name,bank_wallet\n"
            b"201045087208,88.33,test_name,bank_wallet\n"
            b"01263214158,174.53,test_name,orange"
        )
        self.bank_wallet_doc.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.bank_wallet_doc.id))

    def test_valid_account_number_with_bank_card_sheet(self):
        self.bank_card_doc.file=SimpleUploadedFile(
            "bank_card_sheet.csv",
            b"account number / IBAN,amount,full name,bank swift code,transaction type\n"
            b"30164,34.03,test_name,SAIB,salary\n"
            b"EG889262908254516406224392104,476.86,test_name,FAIB,prepaid_card\n"
            b"0937892892264503977777776466365565424444,88.33,test_name,HSBC,credit_card"
        )
        self.bank_card_doc.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.bank_card_doc.id))

    def test_valid_name_with_bank_card_sheet(self):
        self.bank_card_doc.file=SimpleUploadedFile(
            "bank_card_sheet.csv",
            b"account number / IBAN,amount,full name,bank swift code,transaction type\n"
            b"30164,34.03,test%name,SAIB,salary\n"
            b"EG889262908254516406224392104,476.86,test_name,FAIB,prepaid_card"
        )
        self.bank_card_doc.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.bank_card_doc.id))

    def test_valid_bank_swift_code_with_bank_card_sheet(self):
        self.bank_card_doc.file=SimpleUploadedFile(
                "bank_card_sheet.csv",
                b"account number / IBAN,amount,full name,bank swift code,transaction type\n"
                b"30164,34.03,test%name,tttB,salary\n"
                b"EG889262908254516406224392104,476.86,test_name,FAIB,prepaid_card"
        )
        self.bank_card_doc.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.bank_card_doc.id))

    def test_valid_transaction_type_with_bank_card_sheet(self):
        self.bank_card_doc.file=SimpleUploadedFile(
                "bank_card_sheet.csv",
                b"account number / IBAN,amount,full name,bank swift code,transaction type\n"
                b"30164,34.03,test%name,FAIB,fake_trx_type\n"
                b"EG889262908254516406224392104,476.86,test_name,FAIB,prepaid_card"
        )
        self.bank_card_doc.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.bank_card_doc.id))

    def test_duplicate_account_number_witt_bank_card_sheet(self):
        self.bank_card_doc.file=SimpleUploadedFile(
            "bank_card_sheet.csv",
            b"account number / IBAN,amount,full name,bank swift code,transaction type\n"
            b"EG889262908254516406224392104,34.03,test_name,SAIB,salary\n"
            b"09378928922645039,476.86,test_name,HSBC,prepaid_card\n"
            b"09378928922645039,88.33,test_name,HSBC,credit_card"
        )
        self.bank_card_doc.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.bank_card_doc.id))

    def test_total_amount_less_than_max_amount_can_be_disbursed(self):
        self.level.max_amount_can_be_disbursed=30
        self.level.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.bank_card_doc.id))

    def test_has_not_sufficient_budget(self):
        self.budget.current_balance=150
        self.budget.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.bank_wallet_doc.id))

    def test_has_not_disbursement_permission(self):
        self.wallet_moderator.disbursement=False
        self.wallet_moderator.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.bank_wallet_doc.id))

    def test_invalid_issuer(self):
        self.bank_wallet_doc.file=SimpleUploadedFile(
            "bank_wallet_sheet.csv",
            b"mobile number,amount,full name,issuer\n"
            b"1265645842,34.03,test_name,fake\n"
            b"01006260411,476.86,test_name,bank_wallet\n"
            b"201045087208,88.33,test_name,fake\n"
            b"01263214158,174.53,test_name,orange"
        )
        self.bank_wallet_doc.save()
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run(self.bank_wallet_doc.id))

    def test_doc_not_exist(self):
        self.assertFalse(BankWalletsAndCardsSheetProcessor.run('fake_doc_id866564566hjghv'))
