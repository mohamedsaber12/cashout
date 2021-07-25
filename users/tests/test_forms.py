# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from users.tests.factories import SuperAdminUserFactory, AdminUserFactory
from users.forms import SetPasswordForm
from users.models import RootUser

REQUIRED_FIELD_ERROR = 'This field is required.'
PASSWORD_MISMATCH_ERROR = "The two passwords fields didn't match."
WEAK_PASSWORD_ERROR = "Password must contain at least 8 characters"


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
