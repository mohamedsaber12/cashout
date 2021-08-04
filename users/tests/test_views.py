# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import Permission

from users.tests.factories import (
    SuperAdminUserFactory, VMTDataFactory, AdminUserFactory
)
from users.models import (
    SuperAdminUser, Client as ClientModel, Brand, Setup, EntitySetup,
    SupportUser, SupportSetup, CheckerUser, MakerUser, Levels
)
from disbursement.models import Agent, DisbursementDocData
from data.models import Doc, DocReview, FileCategory


class ClientsTests(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:clients'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.super_admin)
        response = self.client.get('/clients/?q=active')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(
            '%s?search=fake_username' % (reverse('users:clients'))
        )
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(
            '%s?q=inactive' % (reverse('users:clients'))
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/clients.html')


class SuperAdminRootSetupTests(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:add_client'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.super_admin)
        response = self.client.get('/client/creation/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('users:add_client'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('users:add_client'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'entity/add_root.html')

    def test_post_method(self):
        self.client.force_login(self.super_admin)
        data = {
            "username": "test_username",
            "email": 'test@em.com'
        }
        response = self.client.post(reverse('users:add_client'), data)
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/')

    def test_post_method_with_accept_vodafone_model(self):
        new_super_admin = SuperAdminUser.objects.create(
            id=110,
            username='super_admin_tt'
        )
        new_super_admin.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding')
        )
        self.client.force_login(new_super_admin)
        data = {
            "username": "test_username",
            "email": 'test@em.com'
        }
        response = self.client.post(reverse('users:add_client'), data)
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/')

    def test_post_method_with_vodafone_facilitator_model(self):
        new_super_admin = SuperAdminUser.objects.create(
            id=110,
            username='super_admin_tt'
        )
        new_super_admin.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='vodafone_facilitator_accept_vodafone_onboarding')
        )
        self.client.force_login(new_super_admin)
        data = {
            "username": "test_username",
            "email": 'test@em.com',
            "vodafone_facilitator_identifier": '654432323456675443'
        }
        response = self.client.post(reverse('users:add_client'), data)
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/')

    def test_post_method_with_default_vodafone_model(self):
        new_super_admin = SuperAdminUser.objects.create(
            id=110,
            username='super_admin_tt'
        )
        new_super_admin.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='vodafone_default_onboarding')
        )
        self.client.force_login(new_super_admin)
        data = {
            "username": "test_username",
            "email": 'test@em.com',
            "smsc_sender_name": 'test',
            "agents_onboarding_choice": "0"
        }
        response = self.client.post(reverse('users:add_client'), data)
        self.assertEqual(response.status_code, 302)


class PinFormViewTests(TestCase):
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
        self.setup = Setup.objects.create(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=False
        )

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:setting-disbursement-pin'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/setting-up/disbursement-pin')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:setting-disbursement-pin'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:setting-disbursement-pin'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/setting-up-disbursement/pin.html')

    def test_post_method(self):
        self.client.force_login(self.root)
        data = {
            "pin": "123456"
        }
        response = self.client.post(reverse('users:setting-disbursement-pin'), data)
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/setting-up/disbursement-makers')


class MakerFormViewTests(TestCase):
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
        self.setup = Setup.objects.create(
                user=self.root,
                levels_setup=True,
                maker_setup=False,
                checker_setup=True,
                category_setup=True,
                pin_setup=True
        )

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:setting-disbursement-makers'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/setting-up/disbursement-makers')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:setting-disbursement-makers'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:setting-disbursement-makers'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/setting-up-disbursement/makers.html')

    def test_post_method(self):
        self.client.force_login(self.root)
        data = {
            'maker-0-first_name': "test",
            'maker-0-last_name': "test",
            'maker-0-mobile_no':"01276375654",
            'maker-0-email': "mk@maker.com",
            "maker-TOTAL_FORMS": 1,
            "maker-INITIAL_FORMS": 0,
            "maker-MIN_NUM_FORMS": 1,
            "maker-MAX_NUM_FORMS": 4
        }
        response = self.client.post(reverse('users:setting-disbursement-makers'), data)
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/setting-up/disbursement-levels')


class CheckerFormViewTests(TestCase):
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
        self.setup = Setup.objects.create(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=False,
            category_setup=True,
            pin_setup=True
        )

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:setting-disbursement-checkers'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/setting-up/disbursement-checkers')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:setting-disbursement-checkers'))

        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:setting-disbursement-checkers'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/setting-up-disbursement/checkers.html')

    def test_post_method(self):
        self.client.force_login(self.root)
        data = {
            'checker-0-first_name': "test",
            'checker-0-last_name': "test",
            'checker-0-mobile_no':"01276375654",
            'checker-0-email': "ch@checker.com",
            "checker-TOTAL_FORMS": 1,
            "checker-INITIAL_FORMS": 0,
            "checker-MIN_NUM_FORMS": 1,
            "checker-MAX_NUM_FORMS": 4
        }
        response = self.client.post(reverse('users:setting-disbursement-checkers'), data)
        self.assertEqual(response.status_code, 200)


class LevelsFormViewTests(TestCase):
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
        self.setup = Setup.objects.create(
            user=self.root,
            levels_setup=False,
            maker_setup=True,
            checker_setup=True,
            category_setup=True,
            pin_setup=True
        )

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:setting-disbursement-levels'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/setting-up/disbursement-levels')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:setting-disbursement-levels'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:setting-disbursement-levels'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/setting-up-disbursement/levels.html')

    def test_post_method(self):
        self.client.force_login(self.root)
        data = {
            'level-0-max_amount_can_be_disbursed': "10000",
            "level-TOTAL_FORMS": 1,
            "level-INITIAL_FORMS": 0,
            "level-MIN_NUM_FORMS": 1,
            "level-MAX_NUM_FORMS": 4
        }
        response = self.client.post(reverse('users:setting-disbursement-levels'), data)
        self.assertEqual(response.status_code, 302)


class CategoryFormViewTests(TestCase):
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
        self.setup = Setup.objects.create(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=False,
            pin_setup=True
        )
        self.entity_setup = EntitySetup.objects.create(
                user=self.super_admin,
                entity=self.root,
                agents_setup=False,
                fees_setup=False
        )

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:setting-disbursement-formats'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/setting-up/disbursement-formats')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:setting-disbursement-formats'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:setting-disbursement-formats'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/setting-up-disbursement/category.html')

    def test_post_method(self):
        self.client.force_login(self.root)
        data = {
            'category-0-first_name': "test",
            'category-0-last_name': "test",
            'category-0-mobile_no':"01276375654",
            'category-0-email': "mk@maker.com",
            "category-TOTAL_FORMS": 1,
            "category-INITIAL_FORMS": 0,
            "category-MIN_NUM_FORMS": 1,
            "category-MAX_NUM_FORMS": 4
        }
        response = self.client.post(reverse('users:setting-disbursement-formats'), data)
        self.assertEqual(response.status_code, 200)


class AddMakerViewTests(TestCase):
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
                agents_setup=False,
                fees_setup=False
        )

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:add_maker'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/members/maker/add/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:add_maker'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:add_maker'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/add_member.html')

    def test_post_method(self):
        self.client.force_login(self.root)
        data = {
            'first_name': "test",
            'last_name': "test",
            'mobile_no':"01276375654",
            'email': "mk@maker.com"
        }
        response = self.client.post(reverse('users:add_maker'), data)

        self.assertEqual(response.status_code, 302)


class AddCheckerViewTests(TestCase):
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
                agents_setup=False,
                fees_setup=False
        )

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:add_checker'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/members/checker/add/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:add_checker'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:add_checker'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/add_member.html')

    def test_post_method(self):
        self.client.force_login(self.root)
        data = {
            'first_name': "test",
            'last_name': "test",
            'mobile_no':"01276375654",
            'email': "ch@checker.com"
        }
        response = self.client.post(reverse('users:add_checker'), data)

        self.assertEqual(response.status_code, 200)


class LevelsViewTests(TestCase):

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
                agents_setup=False,
                fees_setup=False
        )

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:levels'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/levels/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:levels'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:levels'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/add_levels.html')

    def test_post_method(self):
        self.client.force_login(self.root)
        data = {
            'level-0-max_amount_can_be_disbursed': "10000",
            "level-TOTAL_FORMS": 1,
            "level-INITIAL_FORMS": 0,
            "level-MIN_NUM_FORMS": 1,
            "level-MAX_NUM_FORMS": 4
        }
        response = self.client.post(reverse('users:levels'), data)
        self.assertEqual(response.status_code, 302)


class ViewerCreateViewTests(TestCase):
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
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='instant_model_onboarding')
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
                agents_setup=False,
                fees_setup=False
        )

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:add_viewer'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/members/viewer/add/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:add_viewer'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:add_viewer'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'instant_cashin/add_member.html')

    def test_post_method(self):
        self.client.force_login(self.root)
        data = {
            'username': 'test_viewer',
            'first_name': "test",
            'last_name': "test",
            'email': "d@viewer.com",
            'password1': 'o1tw#JLKyAKi#URO3',
            'password2': 'o1tw#JLKyAKi#URO3'
        }
        response = self.client.post(reverse('users:add_viewer'), data)
        self.assertEqual(response.status_code, 302)


class APICheckerCreateViewTests(TestCase):
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
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='instant_model_onboarding')
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
                agents_setup=False,
                fees_setup=False
        )

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:add_api_checker'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/members/api-checker/add/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:add_api_checker'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:add_api_checker'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'instant_cashin/add_member.html')

    def test_post_method(self):
        self.client.force_login(self.root)
        data = {
            'username': 'test_api_checker',
            'first_name': "test",
            'last_name': "test",
            'email': "d@api_checker.com",
            'password1': 'o1tw#JLKyAKi#URO3',
            'password2': 'o1tw#JLKyAKi#URO3'
        }
        response = self.client.post(reverse('users:add_api_checker'), data)
        self.assertEqual(response.status_code, 200)


class EntityBrandingTests(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:entity_branding'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.super_admin)
        response = self.client.get('/settings/branding/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('users:entity_branding'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('users:entity_branding'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/entity_branding.html')

    def test_post_method(self):
        self.client.force_login(self.super_admin)
        data = {
            'color': 'red'
        }
        response = self.client.post(reverse('users:entity_branding'), data)
        self.assertEqual(response.status_code, 302)


class LoginViewTests(TestCase):

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
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='instant_model_onboarding')
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.root.set_password('o1tw#JLKyAKi#URO3')
        self.root.save()

        self.request = RequestFactory()
        self.client = Client()

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get('/user/login/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        response = self.client.get(reverse('users:user_login_view'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(reverse('users:user_login_view'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data/login.html')

    def test_post_method(self):
        data = {
            'username': self.root.username,
            'password': 'o1tw#JLKyAKi#URO3'
        }
        response = self.client.post(reverse('users:user_login_view'), data)
        self.assertEqual(response.status_code, 302)


class ForgotPasswordViewTests(TestCase):

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
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='instant_model_onboarding')
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.root.set_password('o1tw#JLKyAKi#URO3')
        self.root.save()

        self.request = RequestFactory()
        self.client = Client()

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get('/forgot-password/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        response = self.client.get(reverse('users:forgot_password'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(reverse('users:forgot_password'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/forget-password.html')

    def test_post_method(self):
        data = {
            'email': self.root.email,
            'email2': self.root.email
        }
        response = self.client.post(reverse('users:forgot_password'), data)
        self.assertEqual(response.status_code, 200)


class MembersTests(TestCase):

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
            agents_setup=False,
            fees_setup=False
        )

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:members'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get('/members/?search=test_u')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(
            '%s?q=maker' % (reverse('users:members'))
        )
        self.assertEqual(response.status_code, 200)

    def test_members_filter_by_apichecker(self):
        self.client.force_login(self.root)
        response = self.client.get(
            '%s?q=apichecker' % (reverse('users:members'))
        )
        self.assertEqual(response.status_code, 200)

    def test_members_filter_by_viewer(self):
        self.client.force_login(self.root)
        response = self.client.get(
            '%s?q=viewer' % (reverse('users:members'))
        )
        self.assertEqual(response.status_code, 200)

    def test_members_filter_by_fake_data(self):
        self.client.force_login(self.root)
        response = self.client.get(
            '%s?q=fake' % (reverse('users:members'))
        )
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(
            '%s?q=checker' % (reverse('users:members'))
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/members.html')


class SuperAdminSupportSetupCreateViewTests(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:add_support'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.super_admin)
        response = self.client.get('/support/creation/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('users:add_support'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('users:add_support'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'support/add_support.html')

    def test_post_method(self):
        self.client.force_login(self.super_admin)
        data = {
            'username': 'test_support',
            'email': 'test@support.com',
            'can_onboard_entities': False
        }
        response = self.client.post(reverse('users:add_support'), data)
        self.assertEqual(response.status_code, 302)


class SupportUsersListViewTests(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)

        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:support'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.super_admin)
        response = self.client.get('/support/?search=test_support')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('users:support'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('users:support'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'support/list.html')


class ClientsForSupportListViewTests(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.support_user = SupportUser.objects.create(
            username="test_support_user",
            id=112,
            user_type=8
        )
        self.support_setup = SupportSetup.objects.create(
            support_user=self.support_user,
            user_created=self.super_admin
        )
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:support_clients_list'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.support_user)
        response = self.client.get('/support/clients/?search=test_client')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.support_user)
        response = self.client.get(reverse('users:support_clients_list'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.support_user)
        response = self.client.get(reverse('users:support_clients_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'support/clients.html')


class DocumentsForSupportListViewTests(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.support_user = SupportUser.objects.create(
                username="test_support_user",
                id=112,
                user_type=8
        )
        self.support_setup = SupportSetup.objects.create(
                support_user=self.support_user,
                user_created=self.super_admin
        )
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
                agents_setup=False,
                fees_setup=False
        )
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse('users:documents_list', kwargs={'username': self.root.username})
        )
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.support_user)
        response = self.client.get(
            f'/support/documents/{self.root.username}/?search=hghdygtd'
        )
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.support_user)
        response = self.client.get(
            reverse('users:documents_list', kwargs={'username': self.root.username})
        )
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.support_user)
        response = self.client.get(
            reverse('users:documents_list', kwargs={'username': self.root.username})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'support/documents_list.html')


class DocumentForSupportDetailViewTests(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.support_user = SupportUser.objects.create(
                username="test_support_user",
                id=112,
                user_type=8
        )
        self.support_setup = SupportSetup.objects.create(
                support_user=self.support_user,
                user_created=self.super_admin
        )
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
            agents_setup=False,
            fees_setup=False
        )
        self.checker_user = CheckerUser.objects.create(
            id=15,
            username='test_checker_user',
            email='ch@checkersd.com',
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
                content_type__app_label='users', codename='has_disbursement'
        )
        )
        self.checker_user.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding'
        )
        )
        self.maker_user = MakerUser.objects.create(
            id=14,
            username='test_maker_user',
            email='t@mk.com',
            root=self.root,
            user_type=1
        )
        # create doc, doc_review, DisbursementDocData, file category
        file_category = FileCategory.objects.create(
            user_created=self.root
        )
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
            doc=self.doc,
            txn_status = "200",
            has_callback = True,
            doc_status = "5"
        )
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(
            reverse(
                'users:doc_detail',
                kwargs={
                    'username': self.root.username,
                    'doc_id': self.doc.id
                }
            )
        )
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.support_user)
        response = self.client.get(
            f'/support/documents/{self.root.username}/{self.doc.id}/'
        )
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.support_user)
        response = self.client.get(
            reverse(
                'users:doc_detail',
                kwargs={
                    'username': self.root.username,
                    'doc_id': self.doc.id
                }
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.support_user)
        response = self.client.get(
            reverse(
                'users:doc_detail',
                kwargs={
                    'username': self.root.username,
                    'doc_id': self.doc.id
                }
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'support/document_details.html')