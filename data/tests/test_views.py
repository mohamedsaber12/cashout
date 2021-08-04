# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase, Client, RequestFactory, override_settings
from django.urls import reverse
from django.contrib.auth.models import Permission

from users.tests.factories import (
    SuperAdminUserFactory, AdminUserFactory, VMTDataFactory
)
from users.models import (
    Setup, Client as ClientModel, Brand, EntitySetup, CheckerUser, Levels,
    MakerUser
)
from data.models import Doc, DocReview, FileCategory
from utilities.models import Budget, FeeSetup
from disbursement.models import DisbursementDocData


class DisbursementHomeViewTests(TestCase):

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
        self.setup = Setup.objects.create(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=True
        )
        self.entity_setup = EntitySetup.objects.create(
            user=self.super_admin,
            entity=self.root,
            agents_setup=True,
            fees_setup=True
        )
        self.checker_user = CheckerUser.objects.create(
            id=15,
            username='test_checker_user',
            root=self.root,
            user_type=2
        )
        self.level = Levels.objects.create(
            max_amount_can_be_disbursed=1200,
            created=self.root
        )
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
        self.maker_user = MakerUser.objects.create(
            id=14,
            username='test_maker_user',
            email='t@mk.com',
            root=self.root,
            user_type=1
        )
        self.budget = Budget.objects.create(disburser=self.root, current_balance=150)
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
        disb_data_doc = DisbursementDocData.objects.create(
            doc=self.doc,
            txn_status = "200",
            has_callback = True,
            doc_status = "5"
        )
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('data:e_wallets_home'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/disbursement/e-wallets/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('data:e_wallets_home'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('data:e_wallets_home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data/e_wallets_home.html')


class BanksHomeViewTests(TestCase):

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
        self.setup = Setup.objects.create(
                user=self.root,
                levels_setup=True,
                maker_setup=True,
                checker_setup=True,
                category_setup=True,
                pin_setup=True
        )
        self.entity_setup = EntitySetup.objects.create(
                user=self.super_admin,
                entity=self.root,
                agents_setup=True,
                fees_setup=True
        )
        self.checker_user = CheckerUser.objects.create(
                id=15,
                username='test_checker_user',
                root=self.root,
                user_type=2
        )
        self.level = Levels.objects.create(
                max_amount_can_be_disbursed=1200,
                created=self.root
        )
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
        self.maker_user = MakerUser.objects.create(
                id=14,
                username='test_maker_user',
                email='t@mk.com',
                root=self.root,
                user_type=1
        )
        self.budget = Budget.objects.create(disburser=self.root, current_balance=150)
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
        disb_data_doc = DisbursementDocData.objects.create(
                doc=self.doc,
                txn_status = "200",
                has_callback = True,
                doc_status = "5"
        )
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('data:bank_wallets_home'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/disbursement/bank-cards/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('data:bank_wallets_home'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('data:bank_wallets_home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data/bank_sheets_home.html')


class DocumentViewTests(TestCase):

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
        self.setup = Setup.objects.create(
                user=self.root,
                levels_setup=True,
                maker_setup=True,
                checker_setup=True,
                category_setup=True,
                pin_setup=True
        )
        self.entity_setup = EntitySetup.objects.create(
                user=self.super_admin,
                entity=self.root,
                agents_setup=True,
                fees_setup=True
        )
        self.checker_user = CheckerUser.objects.create(
                id=15,
                username='test_checker_user',
                root=self.root,
                user_type=2
        )
        self.level = Levels.objects.create(
                max_amount_can_be_disbursed=1200,
                created=self.root
        )
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
        self.maker_user = MakerUser.objects.create(
                id=14,
                username='test_maker_user',
                email='t@mk.com',
                root=self.root,
                user_type=1
        )
        self.budget = Budget.objects.create(disburser=self.root, current_balance=150)
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
        disb_data_doc = DisbursementDocData.objects.create(
                doc=self.doc,
                txn_status = "200",
                has_callback = True,
                doc_status = "5"
        )
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse('data:doc_viewer', kwargs={'doc_id': self.doc.id})
        )
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get(f'/documents/{self.doc.id}/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.maker_user)
        response = self.client.get(
            reverse('data:doc_viewer', kwargs={'doc_id': self.doc.id})
        )
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(
            reverse('data:doc_viewer', kwargs={'doc_id': self.doc.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data/e_wallets_document_viewer.html')


class DocumentDownloadTests(TestCase):

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
        self.setup = Setup.objects.create(
                user=self.root,
                levels_setup=True,
                maker_setup=True,
                checker_setup=True,
                category_setup=True,
                pin_setup=True
        )
        self.entity_setup = EntitySetup.objects.create(
                user=self.super_admin,
                entity=self.root,
                agents_setup=True,
                fees_setup=True
        )
        self.checker_user = CheckerUser.objects.create(
                id=15,
                username='test_checker_user',
                root=self.root,
                user_type=2
        )
        self.level = Levels.objects.create(
                max_amount_can_be_disbursed=1200,
                created=self.root
        )
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
        self.maker_user = MakerUser.objects.create(
                id=14,
                username='test_maker_user',
                email='t@mk.com',
                root=self.root,
                user_type=1
        )
        self.budget = Budget.objects.create(disburser=self.root, current_balance=150)
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
        disb_data_doc = DisbursementDocData.objects.create(
                doc=self.doc,
                txn_status = "200",
                has_callback = True,
                doc_status = "5"
        )
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
                reverse('data:download_doc', kwargs={'doc_id': self.doc.id})
        )
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get(f'/download_doc/{self.doc.id}/')
        self.assertEqual(response.status_code, 404)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.maker_user)
        response = self.client.get(
                reverse('data:download_doc', kwargs={'doc_id': self.doc.id})
        )
        self.assertEqual(response.status_code, 404)


class FormatListViewTests(TestCase):

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
        self.setup = Setup.objects.create(
                user=self.root,
                levels_setup=True,
                maker_setup=True,
                checker_setup=True,
                category_setup=True,
                pin_setup=True
        )
        self.entity_setup = EntitySetup.objects.create(
                user=self.super_admin,
                entity=self.root,
                agents_setup=True,
                fees_setup=True
        )
        self.checker_user = CheckerUser.objects.create(
                id=15,
                username='test_checker_user',
                root=self.root,
                user_type=2
        )
        self.level = Levels.objects.create(
                max_amount_can_be_disbursed=1200,
                created=self.root
        )
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
        self.maker_user = MakerUser.objects.create(
                id=14,
                username='test_maker_user',
                email='t@mk.com',
                root=self.root,
                user_type=1
        )
        self.budget = Budget.objects.create(disburser=self.root, current_balance=150)
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
        disb_data_doc = DisbursementDocData.objects.create(
                doc=self.doc,
                txn_status = "200",
                has_callback = True,
                doc_status = "5"
        )
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('data:list_format'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/format/list')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('data:list_format'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('data:list_format'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data/formats.html')