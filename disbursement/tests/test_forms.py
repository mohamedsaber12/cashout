# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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
INVALID_ISSUER_ERROR = 'issuer must be one of these \
bank_card / Bank Card / vodafone / etisalat / orange / bank_wallet / aman'
ACCOUNT_NUMBER_ERROR = 'Invalid Account number'
CREDITOR_NAME_ERROR = 'Symbols like !%*+& not allowed in full name'
FIRST_NAME_ERROR = 'Symbols like !%*+& not allowed in first name'
LAST_NAME_ERROR = 'Symbols like !%*+& not allowed in last name'
CREDITOR_NAME_INVALID = 'Invalid name'


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

    # test issuer exist in form data
    def test_issuer_not_exist(self):
        checker_user = CheckerUser(id=15, username='test_checker_user')
        checker_user.root = self.root
        form_data = {}
        form = SingleStepTransactionForm(data=form_data, checker_user=checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['issuer'], [REQUIRED_FIELD_ERROR])

    # test issuer invalid in form data
    def test_issuer_invalid(self):
        checker_user = CheckerUser(id=15, username='test_checker_user')
        checker_user.root = self.root
        form_data = {'issuer': 'xyz'}
        form = SingleStepTransactionForm(data=form_data, checker_user=checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(
            form.errors['issuer'], ['Select a valid choice. xyz is not one of the available choices.'])

    # test creditor_account_number in valid
    def test_creditor_account_number_is_invalid(self):
        checker_user = CheckerUser(id=15, username='test_checker_user')
        checker_user.root = self.root
        form_data = {'creditor_account_number': '12534', 'issuer': 'bank_card'}
        form = SingleStepTransactionForm(data=form_data, checker_user=checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['creditor_account_number'], [ACCOUNT_NUMBER_ERROR])

    # test account name is invalid
    def test_creditor_name_is_invalid(self):
        checker_user = CheckerUser(id=15, username='test_checker_user')
        checker_user.root = self.root
        form_data = {'creditor_name': '', 'issuer': 'bank_card'}
        form = SingleStepTransactionForm(data=form_data, checker_user=checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['creditor_name'], [CREDITOR_NAME_INVALID])

    # test account name has symbol
    def test_creditor_name_has_symbol(self):
        checker_user = CheckerUser(id=15, username='test_checker_user')
        checker_user.root = self.root
        form_data = {'creditor_name': 'ddf%!+uhy', 'issuer': 'bank_card'}
        form = SingleStepTransactionForm(data=form_data, checker_user=checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['creditor_name'], [CREDITOR_NAME_ERROR])

    # test full name has symbol
    def test_full_name_has_symbol(self):
        checker_user = CheckerUser(id=15, username='test_checker_user')
        checker_user.root = self.root
        form_data = {'full_name': 'ddf%!+uhy', 'issuer': 'orange'}
        form = SingleStepTransactionForm(data=form_data, checker_user=checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['full_name'], [CREDITOR_NAME_ERROR])

    # test first name has symbol
    def test_first_name_has_symbol(self):
        checker_user = CheckerUser(id=15, username='test_checker_user')
        checker_user.root = self.root
        form_data = {'first_name': 'ddf%!+uhy', 'issuer': 'aman'}
        form = SingleStepTransactionForm(data=form_data, checker_user=checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['first_name'], [FIRST_NAME_ERROR])

    # test last name has symbol
    def test_last_name_has_symbol(self):
        checker_user = CheckerUser(id=15, username='test_checker_user')
        checker_user.root = self.root
        form_data = {'last_name': 'ddf%!+uhy', 'issuer': 'aman'}
        form = SingleStepTransactionForm(data=form_data, checker_user=checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['last_name'], [LAST_NAME_ERROR])

