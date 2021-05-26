# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import status
from django.test import TestCase

from disbursement.forms import (AgentForm, ExistingAgentForm, PinForm, BalanceInquiryPinForm,
                                SingleStepTransactionForm)
from users.models import RootUser, CheckerUser

REQUIRED_FIELD_ERROR = 'This field is required.'
MOBILE_NUMBER_ERROR = 'Mobile number is not valid'
MOBILE_INVALID_CHOICE_ERROR = 'Select a valid choice. 01021y79732 is not one of the available choices.'
PIN_IS_NUMERIC_ERROR = 'Pin must be numeric'
PIN_IS_INVALID = 'Invalid pin'
AMOUNT_ERROR = 'Enter a whole number.'


class AddAgentFormTests(TestCase):
    def setUp(self):
        self.root = RootUser(id=1, username='test_root_user')
        self.root.root = self.root


    # test msisdn exist in form data
    def test_msisdn_not_exist(self):
        form_data = {}
        form = AgentForm(data=form_data, root=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['msisdn'], [REQUIRED_FIELD_ERROR])

    # test msisdn exist and match agent mobile number
    def test_msisdn_is_mobile_number(self):
        form_data = {'msisdn': '01021469732'}
        form = AgentForm(data=form_data, root=self.root)
        self.assertEqual(form.is_valid(), True)

    # test msisdn exist and not match agent mobile number
    def test_msisdn_not_valid_mobile_number(self):
        form_data = {'msisdn': '01021y79732'}
        form = AgentForm(data=form_data, root=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['msisdn'], [MOBILE_NUMBER_ERROR])


class AddExistingAgentFormTests(TestCase):
    def setUp(self):
        self.root = RootUser(id=1, username='test_root_user')
        self.root.root = self.root
        self.agent_choices = [('01021469732', '01021469732')]


    # test msisdn exist in form data
    def test_msisdn_not_exist(self):
        form_data = {}
        form = ExistingAgentForm(
            data=form_data, root=self.root, agents_choices=self.agent_choices)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['msisdn'], [REQUIRED_FIELD_ERROR])

    # test msisdn exist and match agent mobile number
    def test_msisdn_is_mobile_number(self):
        form_data = {'msisdn': '01021469732'}
        form = ExistingAgentForm(
            data=form_data, root=self.root, agents_choices=self.agent_choices)
        self.assertEqual(form.is_valid(), True)

    # test msisdn not exist in choices
    def test_msisdn_not_exist_in_agents(self):
        form_data = {'msisdn': '01021579732'}
        form = ExistingAgentForm(
            data=form_data, root=self.root, agents_choices=self.agent_choices)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(
            form.errors['msisdn'],
            ['Select a valid choice. 01021579732 is not one of the available choices.'])

    # test msisdn exist and not match agent mobile number
    def test_msisdn_not_valid_mobile_number(self):
        self.agent_choices = [('0102y469732', '0102y469732')]
        form_data = {'msisdn': '0102y469732'}
        form = ExistingAgentForm(
                data=form_data, root=self.root, agents_choices=self.agent_choices)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['msisdn'], [MOBILE_NUMBER_ERROR])


class PinFormTests(TestCase):
    def setUp(self):
        self.root = RootUser(id=1, username='test_root_user')
        self.root.root = self.root

    # test pin exist in form data
    def test_pin_not_exist(self):
        form_data = {}
        form = PinForm(data=form_data, root=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['pin'], [REQUIRED_FIELD_ERROR])

    # test pin exist in form data
    def test_pin_exist_and_numeric(self):
        form_data = {'pin': '323487'}
        form = PinForm(data=form_data, root=self.root)
        self.assertEqual(form.is_valid(), True)

    # test pin exist in form data
    def test_pin_exist_and_not_numeric(self):
        form_data = {'pin': '32t487'}
        form = PinForm(data=form_data, root=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['pin'], [PIN_IS_NUMERIC_ERROR])


class BalanceInquiryPinFormTests(TestCase):

    # test pin exist in form data
    def test_pin_not_exist(self):
        form_data = {}
        form = BalanceInquiryPinForm(data=form_data)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['pin'], [REQUIRED_FIELD_ERROR])

    # test pin exist in form data
    def test_pin_exist_and_numeric(self):
        form_data = {'pin': '323487'}
        form = BalanceInquiryPinForm(data=form_data)
        self.assertEqual(form.is_valid(), True)

    # test pin exist in form data
    def test_pin_exist_and_not_numeric(self):
        form_data = {'pin': '32t487'}
        form = BalanceInquiryPinForm(data=form_data)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['pin'], [PIN_IS_NUMERIC_ERROR])

class SingleStepTransactionFormTests(TestCase):
    def setUp(self):
        self.root = RootUser(id=1, username='test_root_user')
        self.root.root = self.root
        self.root.set_pin('123456')

    # test pin exist in form data
    def test_pin_not_exist(self):
        checker_user = CheckerUser(id=15, username='test_checker_user')
        checker_user.root = self.root
        form_data = {}
        form = SingleStepTransactionForm(data=form_data, checker_user=checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['pin'], [REQUIRED_FIELD_ERROR])

    # test pin exist in form data
    def test_pin_exist_and_invalid(self):
        checker_user = CheckerUser(id=15, username='test_checker_user')
        checker_user.root = self.root
        form_data = {'pin': '323487'}
        form = SingleStepTransactionForm(data=form_data, checker_user=checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['pin'], [PIN_IS_INVALID])

    # test pin exist in form data
    def test_pin_exist_and_not_numeric(self):
        checker_user = CheckerUser(id=15, username='test_checker_user')
        checker_user.root = self.root
        form_data = {'pin': '32t487'}
        form = SingleStepTransactionForm(data=form_data, checker_user=checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['pin'], [PIN_IS_NUMERIC_ERROR])

    # test amount exist in form data
    def test_amount_not_exist(self):
        checker_user = CheckerUser(id=15, username='test_checker_user')
        checker_user.root = self.root
        form_data = {}
        form = SingleStepTransactionForm(data=form_data, checker_user=checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['amount'], [REQUIRED_FIELD_ERROR])

    # test amount invalid in form data
    def test_amount_exist_and_invalid(self):
        checker_user = CheckerUser(id=15, username='test_checker_user')
        checker_user.root = self.root
        form_data = {'amount': 't'}
        form = SingleStepTransactionForm(data=form_data, checker_user=checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['amount'], [AMOUNT_ERROR])