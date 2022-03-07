# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from users.tests.factories import SuperAdminUserFactory, AdminUserFactory
from utilities.forms import BudgetModelForm, BudgetAdminModelForm, IncreaseBalanceRequestForm
from utilities.models import Budget

REQUIRED_FIELD_ERROR = 'This field is required'


class BudgetModelFormTest(TestCase):

    # test new_amount validation
    def test_validate_new_amount(self):
        form_data = {'new_amount': 100}
        budgetForm = BudgetModelForm(
            data=form_data,
            budget_object=Budget(disburser=AdminUserFactory()),
            superadmin_user=SuperAdminUserFactory()
        )
        self.assertEqual(budgetForm.is_valid(), False)


class BudgetAdminModelFormTests(TestCase):

    # test save method
    def test_increase_balance_with_new_added_amount(self):
        form_data = {'add_new_amount': 100}
        budgetForm = BudgetAdminModelForm(data=form_data)
        self.assertEqual(budgetForm.is_valid(), True)
        budget_object=Budget(disburser=AdminUserFactory())
        budgetForm.instance = budget_object
        budgetForm.save()
        self.assertEqual(budget_object.current_balance, form_data['add_new_amount'])


class IncreaseBalanceRequestFormTests(TestCase):

    # test form if transfer type is ==> from_accept_balance
    def test_form_if_transfer_type_from_accept_balance(self):
        form_data = {'type': 'from_accept_balance', 'amount': 100}
        increase_balance_form = IncreaseBalanceRequestForm(data=form_data)
        self.assertEqual(increase_balance_form.is_valid(), False)
        self.assertEqual(increase_balance_form.errors['username'], [REQUIRED_FIELD_ERROR])

    # test form if transfer type is ==> from_bank_transfer
    def test_form_if_transfer_type_from_bank_transfer(self):
        form_data = {'type': 'from_bank_transfer', 'amount': 100}
        increase_balance_form = IncreaseBalanceRequestForm(data=form_data)
        self.assertEqual(increase_balance_form.is_valid(), False)
        self.assertEqual(increase_balance_form.errors['from_bank'], [REQUIRED_FIELD_ERROR])
        self.assertEqual(increase_balance_form.errors['from_account_number'], [REQUIRED_FIELD_ERROR])
        self.assertEqual(increase_balance_form.errors['to_bank'], [REQUIRED_FIELD_ERROR])
        self.assertEqual(increase_balance_form.errors['to_account_number'], [REQUIRED_FIELD_ERROR])
        self.assertEqual(increase_balance_form.errors['from_account_name'], [REQUIRED_FIELD_ERROR])
        self.assertEqual(increase_balance_form.errors['to_account_name'], [REQUIRED_FIELD_ERROR])