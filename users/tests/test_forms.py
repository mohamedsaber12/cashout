# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import Permission

from users.tests.factories import SuperAdminUserFactory, AdminUserFactory
from users.forms import (
    SetPasswordForm, PasswordChangeForm, UserForm, RootCreationForm,
    SupportUserCreationForm, LevelForm
)
from users.models import RootUser, User

REQUIRED_FIELD_ERROR = 'This field is required.'
PASSWORD_MISMATCH_ERROR = "The two passwords fields didn't match."
WEAK_PASSWORD_ERROR = "Password must contain at least 8 characters"
SIMILAR_PASSWORD_ERROR = "Your old password is similar to the new password. "
INCORRECT_PASSWORD_ERROR = "Your old password was entered incorrectly. Please enter it again."
MAX_AMOUNT_CAN_BE_DISBURSED_ERROR = "Amount must be greater than 0"

class PasswordFormTests(TestCase):
    def setUp(self):
        self.root = RootUser(id=1, username='test_root_user')
        self.root.root = self.root

    def test_new_password1_not_exist(self):
        form_data = {}
        form = SetPasswordForm(data=form_data, user=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['new_password1'], [REQUIRED_FIELD_ERROR])

    def test_new_password2_not_exist(self):
        form_data = {}
        form = SetPasswordForm(data=form_data, user=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['new_password2'], [REQUIRED_FIELD_ERROR])

    def test_new_password_mismatch(self):
        form_data = {'new_password1': 'jfhghgfff', 'new_password2': '09hjhfhghgv'}
        form = SetPasswordForm(data=form_data, user=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['new_password2'], [PASSWORD_MISMATCH_ERROR])

    def test_new_password_length(self):
        form_data = {'new_password1': 'nhbg34', 'new_password2': 'nhbg34'}
        form = SetPasswordForm(data=form_data, user=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['new_password2'], [WEAK_PASSWORD_ERROR])

    def test_set_password_form(self):
        form_data = {'new_password1': 'nYU98hbg34M#', 'new_password2': 'nYU98hbg34M#'}
        form = SetPasswordForm(data=form_data, user=self.root)
        self.assertEqual(form.is_valid(), True)

    def test_save_method(self):
        form_data = {'new_password1': 'nYU98hbg34M#', 'new_password2': 'nYU98hbg34M#'}
        form = SetPasswordForm(data=form_data, user=self.root)
        self.assertEqual(form.is_valid(), True)
        self.assertEqual(form.save(), self.root)


class PasswordChangeFormTests(TestCase):
    def setUp(self):
        self.root = RootUser(id=1, username='test_root_user')
        self.root.root = self.root

    def test_new_password1_not_exist(self):
        form_data = {}
        form = PasswordChangeForm(data=form_data, user=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['new_password1'], [REQUIRED_FIELD_ERROR])

    def test_new_password2_not_exist(self):
        form_data = {}
        form = PasswordChangeForm(data=form_data, user=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['new_password2'], [REQUIRED_FIELD_ERROR])

    def test_old_password_not_exist(self):
        form_data = {'new_password1': 'nYU98hbg34M#', 'new_password2': 'nYU98hbg34M#'}
        form = PasswordChangeForm(data=form_data, user=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['old_password'], [REQUIRED_FIELD_ERROR])

    def test_new_password_mismatch(self):
        form_data = {'new_password1': 'jfhghgfff', 'new_password2': '09hjhfhghgv'}
        form = PasswordChangeForm(data=form_data, user=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['new_password2'], [PASSWORD_MISMATCH_ERROR])

    def test_new_password_length(self):
        form_data = {'new_password1': 'nhbg34', 'new_password2': 'nhbg34'}
        form = PasswordChangeForm(data=form_data, user=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['new_password2'], [WEAK_PASSWORD_ERROR])


    def test_similar_password(self):
        self.root.set_password('nYU98hbg34M#')
        self.root.save()
        form_data = {'old_password': 'nYU98hbg34M#', 'new_password1': 'nYU98hbg34M#', 'new_password2': 'nYU98hbg34M#'}
        form = PasswordChangeForm(data=form_data, user=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['new_password2'], [SIMILAR_PASSWORD_ERROR])

    def test_old_password_incorrect(self):
        form_data = {'old_password': 'nYU98hb734M#','new_password1': 'nYU98hbg34M#', 'new_password2': 'nYU98hbg34M#'}
        form = PasswordChangeForm(data=form_data, user=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['old_password'], [INCORRECT_PASSWORD_ERROR])


class UserFormTests(TestCase):

    def setUp(self):
        self.superuser = SuperAdminUserFactory(is_superuser=True)
        self.request = RequestFactory()
        self.request.user = self.superuser

    def test_user_form_username_not_exist(self):
        form_data = {}
        current_form = UserForm
        current_form.request = self.request
        form = current_form(data=form_data)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['username'], [REQUIRED_FIELD_ERROR])

    def test_user_form_username_exist(self):
        form_data = {'username': 'test_test'}
        current_form = UserForm
        current_form.request = self.request
        form = current_form(data=form_data)
        self.assertEqual(form.is_valid(), False)

    def test_user_form_with_not_super_user(self):
        form_data = {'username': 'test_test'}
        current_form = UserForm
        self.request.user = SuperAdminUserFactory()
        current_form.request = self.request
        form = current_form(data=form_data)
        self.assertEqual(form.is_valid(), False)


class RootCreationFormTests(TestCase):

    def setUp(self):
        self.superuser = SuperAdminUserFactory(is_superuser=True)
        self.request = RequestFactory()
        self.request.user = self.superuser

    def test_form_with_vodafone_default_onboarding(self):
        self.request.user.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='vodafone_default_onboarding')
        )
        form_data = {}
        form = RootCreationForm(data=form_data, request=self.request)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['username'], [REQUIRED_FIELD_ERROR])

    def test_form_with_username_exist(self):
        self.request.user = User.objects.create(
            id=213,
            username='test_super_user'
        )
        form_data = {'username': 'test_test'}
        form = RootCreationForm(data=form_data, request=self.request)
        self.assertEqual(form.is_valid(), False)

    def test_root_creation_form(self):
        self.request.user = User.objects.create(
            id=214,
            username='test_super_user'
        )
        self.request.user.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='vodafone_default_onboarding')
        )
        form_data = {
            'username': 'test_root_',
            'email': "r@root.com",
            'vodafone_facilitator_identifier': '545245375674654252',
            'agents_onboarding_choice': '0'
        }
        form = RootCreationForm(data=form_data, request=self.request)
        self.assertEqual(form.is_valid(), True)
        form.save()

    def test_root_creation_form_with_bank_model(self):
        self.request.user = User.objects.create(
            id=214,
            username='test_super_user'
        )
        self.request.user.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='banks_standard_model_onboaring')
        )
        form_data = {
            'username': 'test_root_',
            'email': "r@root.com",
            'vodafone_facilitator_identifier': '545245375674654252',
            'agents_onboarding_choice': '0'
        }
        form = RootCreationForm(data=form_data, request=self.request)
        self.assertEqual(form.is_valid(), True)
        form.save()

    def test_root_creation_form_facilitator_model(self):
        self.request.user = User.objects.create(
            id=214,
            username='test_super_user'
        )
        self.request.user.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='vodafone_facilitator_accept_vodafone_onboarding')
        )
        form_data = {
            'username': 'test_root_',
            'email': "r@root.com",
            'vodafone_facilitator_identifier': '545245375674654252',
            'agents_onboarding_choice': '0'
        }
        form = RootCreationForm(data=form_data, request=self.request)
        self.assertEqual(form.is_valid(), True)
        form.save()


class SupportUserCreationFormTests(TestCase):

    def setUp(self):
        self.request = RequestFactory()

    def test_support_creation_form(self):
        self.request.user = User.objects.create(
            id=214,
            username='test_super_user'
        )
        form_data = {
            'username': 'test_support',
            'email': "r@support.com",
        }
        form = SupportUserCreationForm(data=form_data, request=self.request)
        self.assertEqual(form.is_valid(), True)
        form.save()

    def test_support_creation_form_with_bank_model(self):
        self.request.user = User.objects.create(
                id=214,
                username='test_super_user'
        )
        self.request.user.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='banks_standard_model_onboaring')
        )
        form_data = {
            'username': 'test_support',
            'email': "r@support.com",
        }
        form = SupportUserCreationForm(data=form_data, request=self.request)
        self.assertEqual(form.is_valid(), True)
        form.save()

    def test_support_creation_form_facilitator_model(self):
        self.request.user = User.objects.create(
                id=214,
                username='test_super_user'
        )
        self.request.user.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='vodafone_facilitator_accept_vodafone_onboarding')
        )
        form_data = {
            'username': 'test_support',
            'email': "r@support.com",
        }
        form = SupportUserCreationForm(data=form_data, request=self.request)
        self.assertEqual(form.is_valid(), True)
        form.save()

    def test_support_creation_form_vodafone_default_model(self):
        self.request.user = User.objects.create(
                id=214,
                username='test_super_user'
        )
        self.request.user.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='vodafone_default_onboarding')
        )
        form_data = {
            'username': 'test_support',
            'email': "r@support.com",
        }
        form = SupportUserCreationForm(data=form_data, request=self.request)
        self.assertEqual(form.is_valid(), True)
        form.save()

    def test_support_creation_form_accept_model(self):
        self.request.user = User.objects.create(
                id=214,
                username='test_super_user'
        )
        self.request.user.user_permissions. \
            add(Permission.objects.get(
                content_type__app_label='users', codename='accept_vodafone_onboarding')
        )
        form_data = {
            'username': 'test_support',
            'email': "r@support.com",
        }
        form = SupportUserCreationForm(data=form_data, request=self.request)
        self.assertEqual(form.is_valid(), True)
        form.save()


class LevelFormTests(TestCase):

    def setUp(self):
        self.root = RootUser(
            id=204,
            username='test_root_user'
        )
        self.root.root = self.root
        self.root.save()
        self.request = RequestFactory()
        self.request.user = self.root

    def test_max_amount_can_be_disbursed_no_exist(self):
        form_data = {}
        form = LevelForm(data=form_data, request=self.request)
        self.assertEqual(form.is_valid(), False)
        print('==============================')
        print(form.errors)
        print('==============================')
        self.assertEqual(form.errors['max_amount_can_be_disbursed'], [REQUIRED_FIELD_ERROR])

    def test_max_amount_can_be_disbursed_negative(self):
        form_data = {
            'max_amount_can_be_disbursed': -1
        }
        form = LevelForm(data=form_data, request=self.request)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['max_amount_can_be_disbursed'], [MAX_AMOUNT_CAN_BE_DISBURSED_ERROR])