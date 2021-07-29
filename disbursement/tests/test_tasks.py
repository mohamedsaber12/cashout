# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
from django.contrib.auth.models import Permission

from users.tests.factories import (
    SuperAdminUserFactory, AdminUserFactory, VMTDataFactory
)
from users.models import (
    Client as ClientModel, Brand, CheckerUser, Levels,
    MakerUser
)
from data.models import Doc, DocReview, FileCategory
from utilities.models import Budget, FeeSetup, AbstractBaseDocType
from instant_cashin.models import AbstractBaseIssuer, InstantTransaction

from disbursement.models import DisbursementDocData, DisbursementData
from disbursement.tasks import (
    BulkDisbursementThroughOneStepCashin, check_for_late_disbursement_callback,
    check_for_late_change_profile_callback
)


class BulkDisbursementThroughOneStepCashinTests(TestCase):

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
        self.maker_user = MakerUser(
            id=14,
            username='test_maker_user',
            email='t@mk.com',
            root=self.root,
            user_type=1
        )
        self.maker_user.save()
        self.budget = Budget(disburser=self.root, current_balance=150)
        self.budget.save()
        fees_setup_bank_wallet = FeeSetup(budget_related=self.budget, issuer='bc',
                                          fee_type='f', fixed_value=20)
        fees_setup_bank_wallet.save()
        fees_setup_vodafone = FeeSetup(budget_related=self.budget, issuer='vf',
                                       fee_type='p', percentage_value=2.25)
        fees_setup_vodafone.save()

        # create doc, doc_review, DisbursementDocData, file category
        file_category = FileCategory.objects.create(
            user_created=self.root
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
        disb_doc_data = DisbursementDocData.objects.create(
            doc=self.doc,
            txn_status = "200",
            has_callback = True,
            doc_status = "5"
        )

    def test_bulk_disbursement_through_one_step_cashin(self):
        self.assertTrue(
            BulkDisbursementThroughOneStepCashin.run(
                self.doc.id, self.checker_user.username
            )
        )

    def test_bulk_disbursement_through_one_step_cashin_with_vf_data(self):
        DisbursementData.objects.create(
            doc=self.doc, amount=50, msisdn='01021467656', issuer='vodafone'
        )
        self.assertTrue(
            BulkDisbursementThroughOneStepCashin.run(
                self.doc.id, self.checker_user.username
            )
        )

    def test_bulk_disbursement_through_one_step_cashin_with_et_data(self):
        DisbursementData.objects.create(
            doc=self.doc, amount=50, msisdn='01154350973', issuer='etisalat'
        )
        self.assertFalse(
            BulkDisbursementThroughOneStepCashin.run(
                self.doc.id, self.checker_user.username
            )
        )

    def test_bulk_disbursement_through_one_step_cashin_with_aman_data(self):
        DisbursementData.objects.create(
            doc=self.doc, amount=50, msisdn='01021467656', issuer='aman'
        )
        self.assertTrue(
            BulkDisbursementThroughOneStepCashin.run(
                self.doc.id, self.checker_user.username
            )
        )

    def test_bulk_disbursement_through_one_step_cashin_with_bank_sheet(self):
        self.doc.type_of = AbstractBaseDocType.BANK_CARDS
        self.doc.save()
        self.assertTrue(
            BulkDisbursementThroughOneStepCashin.run(
               self.doc.id, self.checker_user.username
            )
        )

    def test_bulk_disbursement_through_one_step_cashin_with_bank_wallet(self):
        self.doc.type_of = AbstractBaseDocType.BANK_WALLETS
        self.doc.save()
        InstantTransaction.objects.create(
            document=self.doc,
            issuer_type=AbstractBaseIssuer.ORANGE,
            amount=50,
            recipient_name='test',
            anon_recipient='01214214356'
        )
        self.assertTrue(
            BulkDisbursementThroughOneStepCashin.run(
                self.doc.id, self.checker_user.username
            )
        )


class LateChangeProfileCallBack(TestCase):

    def test_check_for_late_change_profile_callback(self):
        self.assertFalse(check_for_late_change_profile_callback())


class LateDisbursementCallBack(TestCase):

    def test_check_for_late_disbursement_callback(self):
        self.assertFalse(check_for_late_disbursement_callback())