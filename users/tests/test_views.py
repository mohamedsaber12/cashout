# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import Permission
from instant_cashin.utils import get_from_env
from users.factories import VariousOnboardingSuperAdminUserFactory
from users.models.access_token import AccessToken
from users.models.onboard_user import OnboardUser, OnboardUserSetup

from users.tests.factories import (
    SuperAdminUserFactory, VMTDataFactory, AdminUserFactory
)
from users.models import (
    SuperAdminUser, Client as ClientModel, Brand, Setup, EntitySetup,
    SupportUser, SupportSetup, CheckerUser, MakerUser, Levels,User,UpmakerUser,InstantAPICheckerUser,InstantAPIViewerUser
)
from disbursement.models import Agent, DisbursementDocData
from data.models import Doc, DocReview, FileCategory
from rest_framework_expiring_authtoken.models import ExpiringToken
from utilities.models import Budget, CallWalletsModerator, FeeSetup, AbstractBaseDocType


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
        response1 = self.client.get(
            '%s?q=h' % (reverse('users:clients'))
        )
        self.assertEqual(response1.status_code, 200)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/clients.html')

    def test_view_url_exists_at_desired_location_but_login_wih_onboarduser(self):
        Onboard_User= OnboardUser.objects.create_user(username="test_onboard_user")
        Onboard_User_Setup= OnboardUserSetup.objects.create(onboard_user=Onboard_User,user_created=self.super_admin)
        self.client.force_login(Onboard_User)
        response = self.client.get(reverse('users:clients'))
        self.assertEqual(response.status_code, 200)


class SuperAdminRootSetup(TestCase):
    def setUp(self):
        self.super_admin = VariousOnboardingSuperAdminUserFactory().instant_apis()
        self.request = RequestFactory()
        self.client = Client()
        self.root=AdminUserFactory()
        self.root.root=self.root
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


    def test_get_success_url(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(
            (reverse('users:add_client'))
        )
        self.assertEqual(response.status_code, 200)

    def test_post_method(self):
        self.client.force_login(self.root)
        data = {
            "username":"root_user",
            'first_name': "test",
            'last_name': "test",
            'mobile_no':"01276375654",
            'email': "mk@maker.com"
            
        }
        response = self.client.post(reverse('users:add_client'), data)
        self.assertEqual(response.status_code, 302)

    def test_for_accept_vodafone(self):
        self.super_admin = VariousOnboardingSuperAdminUserFactory().accept_vodafone()
        self.client.force_login(self.super_admin)
        data = {
            "username":"root_user",
            'first_name': "test",
            'last_name': "test",
            'mobile_no':"01276375654",
            'email': "mk@maker.com"
            
        }
        response = self.client.post(reverse('users:add_client'), data)
        self.assertEqual(response.status_code, 302)

    def test_for_default_vodafone(self):
        self.super_admin =SuperAdminUser.objects.create(username='superadmin')
        self.client.force_login(self.super_admin)
        data = {
            "username":"root_user",
            'first_name': "test",
            'last_name': "test",
            'mobile_no':"01276375654",
            'email': "mk@maker.com",
            'agents_onboarding_choice':'01010101010'
            
        }
        response = self.client.post(reverse('users:add_client'), data)
        self.assertEqual(response.status_code, 200)

    def test_for_onboarduser(self):
        self.super_admin = VariousOnboardingSuperAdminUserFactory.instant_apis()
        Onboard_User= OnboardUser.objects.create_user(username="test_onboard_user")
        Onboard_User_Setup= OnboardUserSetup.objects.create(onboard_user=Onboard_User,user_created=self.super_admin)
        self.client.force_login(Onboard_User)
        data = {
            "username":"root_user",
            'first_name': "test",
            'last_name': "test",
            'mobile_no':"01276375654",
            'email': "mk@maker.com"
            
        }
        response = self.client.post(reverse('users:add_client'), data)
        self.assertEqual(response.status_code, 302)


    def test_superadmin_cancel(self):
        data = {
            "username":self.root.username
        }
        self.client.force_login(self.super_admin)
        response = self.client.post(reverse('users:delete_client', kwargs={'username': self.root.username}))
        self.assertEqual(response.status_code, 302)

    def test_superadmin_cancel_with_onboarduser(self):

        Onboard_User= OnboardUser.objects.create_user(username="test_onboard_user")
        Onboard_User_Setup= OnboardUserSetup.objects.create(onboard_user=Onboard_User,user_created=self.super_admin)
        self.client.force_login(Onboard_User)
        response = self.client.post(reverse('users:delete_client', kwargs={'username': self.root.username}))
        self.assertEqual(response.status_code, 302)

    # def test_superadmin_cancel_with_user_not_exist(self):
    #     self.client.force_login(self.super_admin)
    #     response = self.client.post(reverse('users:delete_client', kwargs={'username': "user"}))
    #     self.assertEqual(response.status_code, 302)


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
            pin_setup=True
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

   

    def test_post_method_with_invalid_pin(self):
        self.client.force_login(self.root)
        data = {
            "pin": "sdsds"
        }
        response = self.client.post(reverse('users:setting-disbursement-pin'), data)
        self.assertEqual(response.status_code, 200)

    def test_post_method_without_pin(self):
        self.client.force_login(self.root)
        data = {}
        response = self.client.post(reverse('users:setting-disbursement-pin'), data)
        self.assertEqual(response.status_code, 200)

    def test_post_method(self):
        self.client.force_login(self.root)
        data = {
            "pin": "123456"
        }
        response = self.client.post(reverse('users:setting-disbursement-pin'), data)
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/setting-up/disbursement-makers')

        
    
    def test_post_method_with_step3(self):
        data = {
            "pin": "123456"
        }
        self.client.force_login(self.root)
        response = self.client.post('%s?to_step=3' % (reverse('users:setting-disbursement-pin')),data)
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/setting-up/disbursement-levels')

    def test_post_method_with_step4(self):
        data = {
            "pin": "123456"
        }
        self.client.force_login(self.root)
        response = self.client.post('%s?to_step=4' % (reverse('users:setting-disbursement-pin')),data)
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/setting-up/disbursement-checkers')

    def test_post_method_with_step5(self):
        data = {
            "pin": "123456"
        }
        self.client.force_login(self.root)
        response = self.client.post('%s?to_step=5' % (reverse('users:setting-disbursement-pin')),data)
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/setting-up/disbursement-formats')
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

    def test_post_method_with_step1(self):
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
        response = self.client.post('%s?to_step=1' % (reverse('users:setting-disbursement-makers')), data)
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/setting-up/disbursement-pin')

    def test_post_method_with_step4(self):
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
        response = self.client.post('%s?to_step=4' % (reverse('users:setting-disbursement-makers')), data)
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/setting-up/disbursement-checkers')

    def test_post_method_with_step5(self):
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
        response = self.client.post('%s?to_step=5' % (reverse('users:setting-disbursement-makers')), data)
        redirect_url = str(response.url).split('?')[0]
        self.assertEqual(redirect_url, '/setting-up/disbursement-formats')




class CheckerFormViewTests(TestCase):
    def setUp(self):
        self.super_admin = SuperAdminUserFactory(is_superuser=True)
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

        self.level = Levels.objects.create(
            max_amount_can_be_disbursed=1200,
            created=self.root
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
            'checker-0-first_name': "test1",
            'checker-0-last_name': "test1",
            'checker-0-mobile_no':"01276375654",
            'checker-0-email': "ch@checker.com",
            'checker-0-level':self.level.id,
            "checker-TOTAL_FORMS": 1,
            "checker-INITIAL_FORMS": 0,
            "checker-MIN_NUM_FORMS": 1,
            "checker-MAX_NUM_FORMS": 4
        }
        response = self.client.post('/setting-up/disbursement-checkers', data)
        self.assertEqual(response.status_code, 302)


    def test_post_method_wih_step1(self):
        self.client.force_login(self.root)
        data = {
            'checker-0-first_name': "test1",
            'checker-0-last_name': "test1",
            'checker-0-mobile_no':"01276375654",
            'checker-0-email': "ch@checker.com",
            'checker-0-level':self.level.id,
            "checker-TOTAL_FORMS": 1,
            "checker-INITIAL_FORMS": 0,
            "checker-MIN_NUM_FORMS": 1,
            "checker-MAX_NUM_FORMS": 4
        }
        response = self.client.post('%s?to_step=1'%(reverse('users:setting-disbursement-checkers')), data)
        self.assertEqual(response.status_code, 302)

    def test_post_method_wih_step2(self):
        self.client.force_login(self.root)
        data = {
            'checker-0-first_name': "test1",
            'checker-0-last_name': "test1",
            'checker-0-mobile_no':"01276375654",
            'checker-0-email': "ch@checker.com",
            'checker-0-level':self.level.id,
            "checker-TOTAL_FORMS": 1,
            "checker-INITIAL_FORMS": 0,
            "checker-MIN_NUM_FORMS": 1,
            "checker-MAX_NUM_FORMS": 4
        }
        response = self.client.post('%s?to_step=2'%(reverse('users:setting-disbursement-checkers')), data)
        self.assertEqual(response.status_code, 302)
    
    def test_post_method_wih_step3(self):
        self.client.force_login(self.root)
        data = {
            'checker-0-first_name': "test1",
            'checker-0-last_name': "test1",
            'checker-0-mobile_no':"01276375654",
            'checker-0-email': "ch@checker.com",
            'checker-0-level':self.level.id,
            "checker-TOTAL_FORMS": 1,
            "checker-INITIAL_FORMS": 0,
            "checker-MIN_NUM_FORMS": 1,
            "checker-MAX_NUM_FORMS": 4
        }
        response = self.client.post('%s?to_step=3'%(reverse('users:setting-disbursement-checkers')), data)
        self.assertEqual(response.status_code, 302)
    


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
    
    def test_post_method_with_step_1(self):
        self.client.force_login(self.root)
        data = {
            'level-0-max_amount_can_be_disbursed': "10000",
            "level-TOTAL_FORMS": 1,
            "level-INITIAL_FORMS": 0,
            "level-MIN_NUM_FORMS": 1,
            "level-MAX_NUM_FORMS": 4
        }
        response = self.client.post('%s?to_step=1'%(reverse('users:setting-disbursement-levels')), data)
        self.assertEqual(response.status_code, 302)
    
    def test_post_method_with_step_2(self):
        self.client.force_login(self.root)
        data = {
            'level-0-max_amount_can_be_disbursed': "10000",
            "level-TOTAL_FORMS": 1,
            "level-INITIAL_FORMS": 0,
            "level-MIN_NUM_FORMS": 1,
            "level-MAX_NUM_FORMS": 4
        }
        response = self.client.post('%s?to_step=2'%(reverse('users:setting-disbursement-levels')), data)
        self.assertEqual(response.status_code, 302)

    def test_post_method_with_step_5(self):
        self.client.force_login(self.root)
        data = {
            'level-0-max_amount_can_be_disbursed': "10000",
            "level-TOTAL_FORMS": 1,
            "level-INITIAL_FORMS": 0,
            "level-MIN_NUM_FORMS": 1,
            "level-MAX_NUM_FORMS": 4
        }
        response = self.client.post('%s?to_step=5'%(reverse('users:setting-disbursement-levels')), data)
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

        self.checker_user = CheckerUser.objects.create(
            id=1695,
            username='test1_checker_user',
            email='ch@checkersd1.com',
            root=self.root,
            user_type=2
        )

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
            'category-0-name': "test",
            'category-0-unique_field':"A-1",
            'category-0-amount_field': "B-1",
            'category-0-issuer_field': "C-1",
            'category-0-no_of_reviews_required ': 1,
            "category-TOTAL_FORMS": 1,
            "category-INITIAL_FORMS": 0,
            "category-MIN_NUM_FORMS": 1,
            "category-MAX_NUM_FORMS": 4
        }
        response = self.client.post(reverse('users:setting-disbursement-formats'), data)
        self.assertEqual(response.status_code, 302)


    def test_post_method_with_step1(self):
        self.client.force_login(self.root)
        data = {
            'category-0-name': "test",
            'category-0-unique_field':"A-1",
            'category-0-amount_field': "B-1",
            'category-0-issuer_field': "C-1",
            'category-0-no_of_reviews_required ': 1,
            "category-TOTAL_FORMS": 1,
            "category-INITIAL_FORMS": 0,
            "category-MIN_NUM_FORMS": 1,
            "category-MAX_NUM_FORMS": 4
        }
        response = self.client.post('%s?to_step=1'%(reverse('users:setting-disbursement-formats')), data)
        self.assertEqual(response.status_code, 302)
    
    def test_post_method_with_step2(self):
        self.client.force_login(self.root)
        data = {
            'category-0-name': "test",
            'category-0-unique_field':"A-1",
            'category-0-amount_field': "B-1",
            'category-0-issuer_field': "C-1",
            'category-0-no_of_reviews_required ': 1,
            "category-TOTAL_FORMS": 1,
            "category-INITIAL_FORMS": 0,
            "category-MIN_NUM_FORMS": 1,
            "category-MAX_NUM_FORMS": 4
        }
        response = self.client.post('%s?to_step=2'%(reverse('users:setting-disbursement-formats')), data)
        self.assertEqual(response.status_code, 302)

    def test_post_method_with_step3(self):
        self.client.force_login(self.root)
        data = {
            'category-0-name': "test",
            'category-0-unique_field':"A-1",
            'category-0-amount_field': "B-1",
            'category-0-issuer_field': "C-1",
            'category-0-no_of_reviews_required ': 1,
            "category-TOTAL_FORMS": 1,
            "category-INITIAL_FORMS": 0,
            "category-MIN_NUM_FORMS": 1,
            "category-MAX_NUM_FORMS": 4
        }
        response = self.client.post('%s?to_step=3'%(reverse('users:setting-disbursement-formats')), data)
        self.assertEqual(response.status_code, 302)

    def test_post_method_with_step4(self):
        self.client.force_login(self.root)
        data = {
            'category-0-name': "test",
            'category-0-unique_field':"A-1",
            'category-0-amount_field': "B-1",
            'category-0-issuer_field': "C-1",
            'category-0-no_of_reviews_required ': 1,
            "category-TOTAL_FORMS": 1,
            "category-INITIAL_FORMS": 0,
            "category-MIN_NUM_FORMS": 1,
            "category-MAX_NUM_FORMS": 4
        }
        response = self.client.post('%s?to_step=4'%(reverse('users:setting-disbursement-formats')), data)
        self.assertEqual(response.status_code, 302)


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
        self.root1 = AdminUserFactory(user_type=3)
        self.root1.root = self.root1
        self.root1.save()
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
    def test_view_url_accessible_by_name_without_disbursment(self):
        self.client.force_login(self.root1)
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



# class ClientFeesSetuptest(TestCase):
#     def setUp(self):
#         self.super_admin = VariousOnboardingSuperAdminUserFactory.default_vodafone()

#     def test_view_url_accessible_by_name(self):
#         self.client.force_login(self.super_admin)
#         token, created = ExpiringToken.objects.get_or_create(user=self.super_admin)

#         response = self.client.post(
#             reverse(
#                 'users:add_fees',
#                 kwargs={
#                     'fees_percentage': '100',
#                 }
#             )
#         )


#         self.assertEqual(response.status_code, 200)

#     def test_view_uses_correct_template(self):
#         self.client.force_login(self.super_admin)
#         token, created = ExpiringToken.objects.get_or_create(user=self.super_admin)
#         data={'fees_percentage':"100"}
#         response = self.client.post(
#             reverse(
#                 'users:add_fees',
#                 kwargs={
#                     'token': token.key,

#                 }
#             ),data
#         )
#         self.assertEqual(response.status_code, 302)
#         self.assertTemplateUsed(response, 'entity/add_client_fees.html')



class SuperAdminFeesProfileTemplateViewtest(TestCase):
    def setUp(self):
        self.super_admin = VariousOnboardingSuperAdminUserFactory.accept_vodafone()
        # self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
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
        self.root.wallet_fees_profile = 'Full'
        self.root.save()


    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.super_admin)

        response = self.client.get(
            
            reverse('users:super_fees_profile')
        )
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(
           reverse('users:super_fees_profile')

        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/fees_profile.html')


class ClientFeesUpdatetest(TestCase):
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

        self.Onboard_User= OnboardUser.objects.create_user(username="test_onboard_user")
        self.Onboard_User_Setup= OnboardUserSetup.objects.create(onboard_user=self.Onboard_User,user_created=self.super_admin)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.Onboard_User)

        response = self.client.get(
            
           reverse('users:update_fees_profile', kwargs={'username': self.root.username})
        )
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.Onboard_User)
        data={'fees_percentage':'100'}
        response = self.client.post(
           reverse('users:update_fees_profile', kwargs={'username': self.root.username}),data

        )
        self.assertEqual(response.status_code, 302)
        # self.assertTemplateUsed(response, 'onboard/update_fees_profile.html')
class testCustomClientFeesProfilesUpdateView(TestCase):
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

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.super_admin)
        data={'fees_percentage':'100'}
        response = self.client.post(
           reverse('users:update_fees', kwargs={'username': self.root.username}),data
        )

        self.assertEqual(response.status_code, 302)
        '''how cover the get in post request and why template didn't work'''
        # self.assertTemplateUsed(response, 'entity/update_fees.html')

        
class ClientFeesSetup(TestCase):

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

        self.entity_setup = EntitySetup.objects.create(
            user=self.super_admin,
            entity=self.root,
            agents_setup=False,
            fees_setup=True
        )

    # def test_view_url_exists_at_desired_location(self):
    #     self.client.force_login(self.super_admin)
    #     data={'fees_percentage':'100'}
    #     token, created = ExpiringToken.objects.get_or_create(user=self.root)
    #     response = self.client.post(                
    #         reverse('users:add_fees',  kwargs={'token': token.key}),data
    #     )
    #     self.assertEqual(response.status_code, 302)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.super_admin)
        token, created = ExpiringToken.objects.get_or_create(user=self.root)
        response = self.client.get(                
            reverse('users:add_fees',  kwargs={'token': token.key})
        )
        self.assertEqual(response.status_code, 302)
        '''how cover the get in post request and why template didn't work'''
        # self.assertTemplateUsed(response, 'entity/update_fees.html')




from users.models import RootUser
class ChangePinViewTests(TestCase):
    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = RootUser.objects.create(
                    username="integration_admin",
                    email="integration_admin@paymob.com",
                    user_type=3,
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
        response = self.client.get(reverse('users:change_pin'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:change_pin'))
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:change_pin'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:change_pin'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/change_pin.html')

    def test_post_method(self):
        self.root.set_password("123456")
        self.root.save()
        self.client.force_login(self.root)
        data = {
            'new_pin': "123456",
            'password': '123456'
        }
        response = self.client.post(reverse('users:change_pin'), data)
        self.assertEqual(response.status_code, 200)

    def test_post_method_with_invalid_password(self):
        self.root.set_password("123456")
        self.root.save()
        self.client.force_login(self.root)
        data = {
            'new_pin': "123456",
            'password': '123d456'
        }
        response = self.client.post(reverse('users:change_pin'), data)
        self.assertEqual(response.status_code, 200)

    def test_post_method_with_invalid_pin(self):
        self.root.set_password("123456")
        self.root.save()
        self.client.force_login(self.root)
        data = {
            'new_pin': "1sdds6",
            'password': '123456'
        }
        response = self.client.post(reverse('users:change_pin'), data)
        self.assertEqual(response.status_code, 200)

class vodafone_change_pin_view_test(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = RootUser.objects.create(
                    username="default_vodafone_admin",
                    email="integration_admin@paymob.com",
                    user_type=3,
                    password=123456
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
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement')
        )
        self.root.user_permissions.add(
                Permission.objects.get(content_type__app_label="users", codename="vodafone_default_onboarding")
        )
        self.root.save()
        self.client_user = ClientModel(client=self.root, creator=self.super_admin, agents_onboarding_choice=0)
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
        response = self.client.get(reverse('users:vodafone_change_pin'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:vodafone_change_pin'))
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:vodafone_change_pin'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:vodafone_change_pin'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/vodafone_change_pin.html')

    def test_post_method(self):
        self.root.set_password("123456")
        self.root.save() 
        self.client.force_login(self.root)
        data = {
            'new_pin': "123456",
            'password': '123456',
            'confirm_pin':"123456"
        }
        response = self.client.post(reverse('users:vodafone_change_pin'), data)
        self.assertEqual(response.status_code, 200)

    def test_post_method_with_invalid_password(self):
        self.root.set_password("123456")
        self.root.save()
        self.client.force_login(self.root)
        data = {
            'new_pin': "123456",
            'password': '123d456',
            'confirm_pin':"123456"

        }
        response = self.client.post(reverse('users:change_pin'), data)
        self.assertEqual(response.status_code, 200)

    def test_post_method_with_invalid_pin(self):
        self.root.set_password("123456")
        self.root.save()
        self.client.force_login(self.root)
        data = {
            'new_pin': "1sdds6",
            'password': '123456',
            'confirm_pin':"123456"

        }
        response = self.client.post(reverse('users:change_pin'), data)
        self.assertEqual(response.status_code, 200)

    def test_post_method_with_old_pin(self):
        self.root.set_password("123456")
        self.root.set_pin("123456")
        self.root.save()
        self.client.force_login(self.root)
        data = {
            'new_pin': "123456",
            'password': '123456',
            'confirm_pin':"123456"

        }
        response = self.client.post(reverse('users:change_pin'), data)
        self.assertEqual(response.status_code, 200)

    def test_post_method_with_pin_not_equal_confirm_pin(self):
        self.root.set_password("123456")
        self.root.set_pin("123456")
        self.root.save()
        self.client.force_login(self.root)
        data = {
            'new_pin': "123456",
            'password': '123456',
            'confirm_pin':"123486"

        }
        response = self.client.post(reverse('users:change_pin'), data)
        self.assertEqual(response.status_code, 200)
        



class OnboardingNewMerchantTests(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory(username=get_from_env("ACCEPT_VODAFONE_INTERNAL_SUPERADMIN"))
        self.super_admin1 = SuperAdminUserFactory(username=get_from_env("INTEGTATION_PATCH_SUPERADMIN"))
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin1)
        self.system_user = User.objects.create(username='system_user',user_type=0,is_staff=True,is_superuser=True)
        self.token = AccessToken()
        self.token.save()
        self.request = RequestFactory()
        self.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:creation_admin',kwargs={"token": self.token.token}))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.system_user)
        response = self.client.get(f'/creation/admin/{self.token.token}/?'+
        "user_name=user_name&admin_email=admin_email&idms_user_id=idms_user_id&mobile_number=56556656565&mid=5545")
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.system_user)
        response = self.client.get("%s?user_name=user_name&admin_email=admin_email&idms_user_id=idms_user_id&mobile_number=56556656565&mid=5545" %(reverse('users:creation_admin',kwargs={"token": self.token.token})))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.system_user)
        response = self.client.get("%s?user_name=user_name&admin_email=admin_email&idms_user_id=idms_user_id&mobile_number=56556656565&mid=5545" %(reverse('users:creation_admin',kwargs={"token": self.token.token})))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/creation_admin.html')

    def test_post_method(self):
        self.client.force_login(self.system_user)
        data = {
            'username': 'tes8t',
            'email': 'tes7t@support.com',
            'idms_user_id': 'sss8s88',
            'mobile_number':"012449545554",
            'mid':541585,
            'onboard_business_model':"portal"
        }
        response = self.client.post((reverse('users:creation_admin', kwargs={'token': self.token.token})), data)
        self.assertEqual(response.status_code, 302)

    def test_post_method_with_instant_user(self):
        self.client.force_login(self.system_user)
        data = {
            'username': 'tesrt',
            'email': 'tesrt@support.com',
            'idms_user_id': 'ssss88',
            'mobile_number':"012447545554",
            'mid':54155,
            'onboard_business_model':"integration"
        }
        response = self.client.post((reverse('users:creation_admin', kwargs={'token': self.token.token})), data)
        self.assertEqual(response.status_code, 302)


class LevelUpdateViewTest(TestCase):
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
        self.checker_user = CheckerUser.objects.create(
            id=15,
            username='test_checker_user',
            email='ch@checkersd.com',
            root=self.root,
            user_type=2
        )
        self.level1 = Levels.objects.create(
            max_amount_can_be_disbursed=1200,
            created=self.root
        )
        self.level2 = Levels.objects.create(
            max_amount_can_be_disbursed=1300,
            created=self.root
        )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:edit_level', kwargs={'username': self.checker_user.username}))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:edit_level', kwargs={'username': self.checker_user.username}))
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:edit_level', kwargs={'username': self.checker_user.username}))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:edit_level', kwargs={'username': self.checker_user.username}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/level_update.html')

    def test_post_method(self):
        # self.root.set_password("123456")
        # self.root.save() 
        self.client.force_login(self.root)
        data = {
            'level':self.level1.id
        }
        response = self.client.post(reverse('users:edit_level', kwargs={'username': self.checker_user.username}), data)
        self.assertEqual(response.status_code, 302)

class OTPLoginViewTest(TestCase):
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
        self.checker_user = CheckerUser.objects.create(
            id=15,
            username='test_checker_user',
            email='ch@checkersd.com',
            root=self.root,
            user_type=2
        )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:otp_login'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.checker_user)
        response = self.client.get(reverse('users:otp_login'))
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.checker_user)
        response = self.client.get(reverse('users:otp_login'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.checker_user)
        response = self.client.get(reverse('users:otp_login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'two_factor/login.html')

    def test_post_method(self):
        # self.root.set_password("123456")
        # self.root.save() 
        self.client.force_login(self.checker_user)
        data = {
            'otp_token':15555
        }
        response = self.client.post(reverse('users:otp_login'), data)
        self.assertEqual(response.status_code, 200)


class RedirectPageViewTest(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = AdminUserFactory(user_type=2)
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
            id=1558,
            username='test_checker_user',
            email='ch@checkersd.com',
            root=self.root,
            user_type=2
        )
        self.upmaker=UpmakerUser.objects.create_user(
            hierarchy=1,
            username='test_upmaker_user',
            root=self.root,
            email='test_upmaker_user@gmail.com'

        )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:redirect'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.checker_user)
        response = self.client.get(reverse('users:redirect'))
        self.assertEqual(response.status_code, 302)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.checker_user)
        response = self.client.get(reverse('users:redirect'))
        self.assertEqual(response.status_code, 302)

    # def test_view_uses_correct_template(self):
    #     self.client.force_login(self.checker_user)
    #     response = self.client.get(reverse('users:redirect'))
    #     self.assertEqual(response.status_code, 302)
    #     self.assertTemplateUsed(response, 'users/redirect_page.html')

    def test_view_url_with_status_disbursement(self):
        self.client.force_login(self.upmaker)
        response = self.client.get("%s?status=disbursement"%(reverse('users:redirect')))
        self.assertEqual(response.status_code, 302)

    def test_view_url_with_other_status(self):
        self.client.force_login(self.upmaker)
        response = self.client.get((reverse('users:redirect')))
        self.assertEqual(response.status_code, 200)

class login_viewTest(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = RootUser.objects.create(
                    username="Careem_Admin",
                    email="integration_admin@paymob.com",
                    user_type=3,
                    password=123456
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
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement')
        )
        self.root.user_permissions.add(
                Permission.objects.get(content_type__app_label="users", codename="vodafone_default_onboarding")
        )
        self.root.save()
        self.client_user = ClientModel(client=self.root, creator=self.super_admin, agents_onboarding_choice=0)
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
        self.checker_user = CheckerUser.objects.create(
            id=1558,
            username='test_checker_user',
            email='ch896@checkersd.com',
            root=self.root,
            user_type=2
        )
        self.checker_user.user_permissions.add(
                Permission.objects.get(content_type__app_label="users", codename="vodafone_default_onboarding")
        )
        self.checker_user1 = CheckerUser.objects.create(
            id=1595,
            username='test_chcecker_user',
            email='ch85@checkersd.com',
            root=self.root,
            user_type=2
        )

        self.checker_user.save()
        self.upmaker=UpmakerUser.objects.create_user(
            hierarchy=1,
            username='test_upmaker1_user',
            root=self.root,
            email='test_upmaker_user1@gmail.com'

        )
        self.instantapichecker=InstantAPICheckerUser.objects.create(username="InstantAPICheckerUser", root=self.root,user_type=6,
            email='user1@gmail.com')
        self.instantapiviewer=InstantAPIViewerUser.objects.create(username="InstantAPIViewerUser", root=self.root,user_type=7,
            email='user12@gmail.com')
        self.instantapiviewer1=InstantAPIViewerUser.objects.create(username="InstaantAPIViewerUser", root=self.root,user_type=7,is_active=False
            ,email='usera12@gmail.com')

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get(reverse('users:user_login_view'))
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        response = self.client.get(reverse('users:user_login_view'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(reverse('users:user_login_view'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'data/login.html')

    def test_view_url_accessible_by_name1(self):
        self.client.force_login(self.checker_user)
        response = self.client.get(reverse('users:user_login_view'))
        self.assertEqual(response.status_code, 302)

    def test_view_url_accessible_by_name2(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:user_login_view'))
        self.assertEqual(response.status_code, 302)

    def test_view_url_accessible_by_name3(self):
        self.client.force_login(self.upmaker)
        response = self.client.get(reverse('users:user_login_view'))
        self.assertEqual(response.status_code, 302)

    def test_view_url_accessible_by_name4(self):
        response = self.client.get("%s?refresh=true"%(reverse('users:user_login_view')))
        self.assertEqual(response.status_code, 302)

    def test_view_url_accessible_by_name_with_refersh(self):
        self.client.force_login(self.upmaker)
        response = self.client.get("%s?refresh=true"%(reverse('users:user_login_view')))
        self.assertEqual(response.status_code, 302)

    def test_view_url_accessible_by_name_for_super_admin(self):
        self.super_admin.set_password("123456")
        self.super_admin.save()
        data={
            "username":self.super_admin.username,
            "password":"123456"
        }
        response = self.client.post(reverse('users:user_login_view'),data)
        self.assertEqual(response.status_code, 302)

    def test_view_url_accessible_by_name_for_root(self):
        self.root.set_password("123456")
        self.root.save()
        data={
            "username":self.root.username,
            "password":"123456"
        }
        response = self.client.post(reverse('users:user_login_view'),data)
        self.assertEqual(response.status_code, 302)

    def test_view_url_accessible_by_name_for_checker_user(self):
        self.checker_user.set_password("123456")
        self.checker_user.save()
        data={
            "username":self.checker_user.username,
            "password":"123456"
        }
        response = self.client.post(reverse('users:user_login_view'),data)
        self.assertEqual(response.status_code, 302)

    def test_view_url_accessible_by_name_for_checker_user1(self):
        self.checker_user1.set_password("123456")
        self.checker_user1.save()
        data={
            "username":self.checker_user1.username,
            "password":"123456"
        }
        response = self.client.post(reverse('users:user_login_view'),data)
        self.assertEqual(response.status_code, 302)

    def test_view_url_accessible_by_name_for_instantapichecker(self):
        self.instantapichecker.set_password("123456")
        self.instantapichecker.save()
        data={
            "username":self.instantapichecker.username,
            "password":"123456"
        }
        response = self.client.post(reverse('users:user_login_view'),data)
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name_for_instantapiviewer(self):
        self.instantapiviewer.set_password("123456")
        self.instantapiviewer.save()
        data={
            "username":self.instantapiviewer.username,
            "password":"123456"
        }
        response = self.client.post(reverse('users:user_login_view'),data)
        self.assertEqual(response.status_code, 302)

    def test_view_url_accessible_by_name_for_upmaker(self):
        self.upmaker.set_password("123456")
        self.upmaker.save()
        data={
            "username":self.upmaker.username,
            "password":"123456"
        }
        response = self.client.post(reverse('users:user_login_view'),data)
        self.assertEqual(response.status_code, 302)

    def test_view_url_accessible_by_name_deactive_user(self):
        self.root.set_password("123456")
        self.root.is_active=False
        self.root.save()
        data={
            "username":self.root.username,
            "password":"123456"
        }
        response = self.client.post(reverse('users:user_login_view'),data)
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name_with_invalid_login_credentials(self):
        self.instantapiviewer1.set_password("123456")
        self.instantapiviewer1.save()
        data={
            "username":self.instantapiviewer1.username,
            "password":"12856"
        }
        response = self.client.post(reverse('users:user_login_view'),data)
        self.assertEqual(response.status_code, 200)
    
    
class ourlogoutTest(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = RootUser.objects.create(
                    username="Careem_Admin",
                    email="integration_admin@paymob.com",
                    user_type=3,
                    password=123456
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
        self.root.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement')
        )
        self.root.user_permissions.add(
                Permission.objects.get(content_type__app_label="users", codename="vodafone_default_onboarding")
        )
        self.root.save()
        self.client_user = ClientModel(client=self.root, creator=self.super_admin, agents_onboarding_choice=0)
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

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get(reverse('users:logout'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:logout'))
        self.assertEqual(response.status_code, 302)


class CallbackURLEditTest(TestCase):

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
        self.checker_user = CheckerUser.objects.create(
            id=15,
            username='test_checker_user',
            email='ch@checkersd.com',
            root=self.root,
            user_type=2
        )

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:api_viewer_callback',kwargs={"username":self.checker_user.username}))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:api_viewer_callback',kwargs={"username":self.checker_user.username}))
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:api_viewer_callback',kwargs={"username":self.checker_user.username}))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse('users:api_viewer_callback',kwargs={"username":self.checker_user.username}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/callback_url.html')

    def test_post_method(self):
        # self.root.set_password("123456")
        # self.root.save() 
        self.client.force_login(self.root)
        data = {
            'callback_url':"www.google.com"
        }
        response = self.client.post(reverse('users:api_viewer_callback',kwargs={"username":self.checker_user.username}), data)
        self.assertEqual(response.status_code, 302)



class OnboardUsersListViewTest(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory(is_superuser=True)
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

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:onboard_user'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.super_admin)
        response = self.client.get('/onboard-user/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('users:onboard_user'))
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name_with_search(self):
        self.client.force_login(self.super_admin)
        response = self.client.get('%s?search=test'%(reverse('users:onboard_user')))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('users:onboard_user'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboard/list.html')




class SuperAdminOnboardSetupCreateViewTest(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory(is_superuser=True)
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

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:add_onboard_user'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.super_admin)
        response = self.client.get('/onboard-user/creation/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('users:add_onboard_user'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('users:add_onboard_user'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboard/add_onboard_user.html')

    def test_post_method(self):
        self.client.force_login(self.super_admin)
        data={
            "username":"test",
            "email":"test@gmail.com"
        }
        response = self.client.post(reverse('users:add_onboard_user'),data)
        self.assertEqual(response.status_code, 302)

class change_passwordTest(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory(is_superuser=True)
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

    # def test_redirect_if_not_logged_in(self):
    #     response = self.client.get(reverse('users:change_password',kwargs={"user":self.root.username}))
    #     self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('users:change_password',kwargs={"user":self.root.username}))
        self.assertEqual(response.status_code, 200)

    # def test_view_url_accessible_by_name(self):
    #     self.client.force_login(self.super_admin)
    #     response = self.client.get(reverse('users:change_password',kwargs={"user":self.root.username}))
    #     self.assertEqual(response.status_code, 200)

    # def test_view_uses_correct_template(self):
    #     self.client.force_login(self.super_admin)
    #     response = self.client.get(reverse('users:change_password',kwargs={"user":self.root.username}))
    #     self.assertEqual(response.status_code, 200)
    #     self.assertTemplateUsed(response, 'data/change_password.html')

    def test_post_method(self):
        self.root.set_password("123456")
        self.super_admin.set_password("123456")
        self.super_admin.save()
        self.root.save()
        self.client.force_login(self.super_admin)

        data={
            "new_password1":"12345678@lllAA",
            "new_password2":"12345678@lllAA",
            "old_password":"123456"

        }
        response = self.client.post(reverse('users:change_password',kwargs={"user":self.root.username}),data)
        self.assertEqual(response.status_code, 302)

    def test_post_method_with_invalid_form(self):
        self.root.set_password("123456")
        self.super_admin.set_password("123456")
        self.super_admin.save()
        self.root.save()
        self.client.force_login(self.super_admin)

        data={
            "new_password1":"1234569a78",
            "new_password2":"123456978",
            "old_password":"123456"

        }
        response = self.client.post(reverse('users:change_password',kwargs={"user":self.root.username}),data)
        self.assertEqual(response.status_code, 200)

    







class UserDeleteViewTest(TestCase):
    def setUp(self):
        self.super_admin = SuperAdminUserFactory(is_superuser=True)
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

        self.support_user=SupportUser.objects.create_user(username="support_user",email="support_user@gmail.com")
        self.support_user_setup=SupportSetup.objects.create(support_user=self.support_user, user_created=self.super_admin)

    # def test_post_method(self):
    #     self.client.force_login(self.super_admin)

    #     data={
    #         "client":True,
    #         "user_id":33,
    #     }
    #     response = self.client.post(reverse('users:delete'), data, **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'})
    #     self.assertEqual(response.status_code, 200)

    # def test_post_method_invalid(self):
    #     self.client.force_login(self.super_admin)

    #     data={
    #         "user_id":33,
    #     }
    #     response = self.client.post(reverse('users:delete'), data, **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'})
    #     self.assertEqual(response.status_code, 200)

    def test_post_method_for_support_user(self):
        self.client.force_login(self.super_admin)

        data={
            "support":True,
            "user_id":self.support_user_setup.id,
        }
        response = self.client.post(reverse('users:delete'), data, **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'})
        self.assertEqual(response.status_code, 200)

class SupervisorUsersListView(TestCase):
    
    def setUp(self):
        self.super_admin = SuperAdminUserFactory(is_superuser=True)
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

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:supervisor'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.super_admin)
        response = self.client.get('/supervisor/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('users:supervisor'))
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name_with_search(self):
        self.client.force_login(self.super_admin)
        response = self.client.get("/supervisor/?search=15")
        self.assertEqual(response.status_code, 200)

class SuperAdminSupervisorSetupCreateViewTest(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory(is_superuser=True)
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

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:add_supervisor_user'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.super_admin)
        response = self.client.get('/supervisor/creation/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('users:add_supervisor_user'))
        self.assertEqual(response.status_code, 200)
        
    def test_post_method(self):
        self.root.set_password("123456")
        self.super_admin.set_password("123456")
        self.super_admin.save()
        self.root.save()
        self.client.force_login(self.super_admin)

        data={
            "username":"test@lllAA",
            "email":"test8@gmai.net",

        }
        response = self.client.post(reverse('users:add_supervisor_user'),data)
        self.assertEqual(response.status_code, 302)


    
class SupervisorReactivateSupportView(TestCase):
    def setUp(self):
        self.super_admin = SuperAdminUserFactory(is_superuser=True)
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

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:add_supervisor_user'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.super_admin)
        response = self.client.get('/supervisor/creation/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('users:add_supervisor_user'))
        self.assertEqual(response.status_code, 200)
        
    def test_post_method(self):
        self.root.set_password("123456")
        self.super_admin.set_password("123456")
        self.super_admin.save()
        self.root.save()
        self.client.force_login(self.super_admin)

        data={
            "username":"test@lllAA",
            "email":"test8@gmai.net",

        }
        response = self.client.post(reverse('users:add_supervisor_user'),data)
        self.assertEqual(response.status_code, 302)


class OnboardingNewInstantAdminTest(TestCase):

    def setUp(self) :
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
        response = self.client.get(reverse('users:support_clients_credentials'))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.support_user)
        response = self.client.get('/support/clients/Credentials')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.support_user)
        response = self.client.get(reverse('users:support_clients_credentials'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.support_user)
        response = self.client.get(reverse('users:support_clients_credentials'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'support/integration_client_credentials.html')

    def test_post_method(self):
        self.client.force_login(self.support_user)

        data={
            "client_name":"testlllAA",
        }
        response = self.client.post(reverse('users:support_clients_credentials'),data)
        self.assertEqual(response.status_code, 200)
    

class ClientCredentialsDetailsTest(TestCase):

    def setUp(self) :
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

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('users:support_clients_credentials_details', kwargs={'client_id':1}))
        self.assertRedirects(response, '/user/login/')

    def test_view_url_exists_at_desired_location(self):
        self.client.force_login(self.support_user)
        response = self.client.get(f'/support/clients/Credentials/{self.client_user.id}')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        self.client.force_login(self.support_user)
        response = self.client.get(reverse('users:support_clients_credentials_details', kwargs={'client_id':self.client_user.id}))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.force_login(self.support_user)
        response = self.client.get(reverse('users:support_clients_credentials_details', kwargs={'client_id':self.client_user.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'support/client_Credentials_details.html')

    

class toggle_clientTests(TestCase):
    def setUp(self) :
        self.super_admin = SuperAdminUserFactory(is_superuser=True)
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.request = RequestFactory()
        self.client = Client()
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

    def test_post_method(self):
        self.client.force_login(self.super_admin)

        data={
            "user_id":self.client_user.id,
        }
        response = self.client.post(reverse('users:toggle'), data, **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'})
        self.assertEqual(response.status_code, 200)
