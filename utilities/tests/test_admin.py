# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.admin.models import LogEntry
from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from users.tests.factories import AdminUserFactory, SuperAdminUserFactory
from utilities.admin import BudgetAdmin, LogEntryAdmin
from utilities.forms import BudgetAdminModelForm
from utilities.models import Budget

BUDGET_READ_ONLY_FIELDS_WITH_SUPERUSER = [
    'total_disbursed_amount',
    'updated_at',
    'created_at',
    'created_by',
    'current_balance',
    'hold_balance',
]
BUDGET_READ_ONLY_FIELDS_WITHOUT_SUPERUSER = [
    'total_disbursed_amount',
    'updated_at',
    'created_at',
    'created_by',
    'current_balance',
    'hold_balance',
    'disburser',
    'current_balance',
    'total_disbursed_amount',
    'updated_at',
]


class CurrentRequest(object):
    def __init__(self, user=None):
        self.user = user


class LogEntryAdminTests(TestCase):
    def setUp(self):
        self.logEntryAdmin = LogEntryAdmin(model=LogEntry, admin_site=AdminSite())

    # check if log entry admin model has add permission
    def test_has_add_permission(self):
        self.assertEqual(self.logEntryAdmin.has_add_permission(CurrentRequest), False)

    # check if  log entry admin model has delete permission
    def test_has_delete_permission(self):
        self.assertEqual(
            self.logEntryAdmin.has_delete_permission(CurrentRequest), False
        )

    # check if log entry admin model has change permission
    def test_has_change_permission(self):
        self.assertEqual(
            self.logEntryAdmin.has_change_permission(CurrentRequest), False
        )


class BudgetAdminTests(TestCase):
    def setUp(self):
        self.budgetAdmin = BudgetAdmin(model=Budget, admin_site=AdminSite())
        self.superuser = SuperAdminUserFactory(is_superuser=True)
        self.not_superuser = SuperAdminUserFactory(is_superuser=False)

    # test read only fields
    def test_get_readonly_fields_with_superuser(self):
        self.assertEqual(
            self.budgetAdmin.get_readonly_fields(CurrentRequest(user=self.superuser)),
            BUDGET_READ_ONLY_FIELDS_WITH_SUPERUSER,
        )

    # test read only fields
    def test_get_readonly_fields_without_superuser(self):
        self.assertEqual(
            self.budgetAdmin.get_readonly_fields(
                CurrentRequest(user=self.not_superuser)
            ),
            BUDGET_READ_ONLY_FIELDS_WITHOUT_SUPERUSER,
        )

    # check if budget admin model has add permission
    # def test_has_add_permission_raise_permission_error(self):
    #     self.assertRaises(
    #         PermissionError,
    #         self.budgetAdmin.has_add_permission,
    #         CurrentRequest(user=self.not_superuser)
    #     )

    # check if budget admin model has add permission
    def test_has_add_permission(self):
        self.assertEqual(
            self.budgetAdmin.has_add_permission(CurrentRequest(user=self.superuser)),
            True,
        )

    # test save model raise permission error
    def test_save_model_raise_permission_error(self):
        budget_obj = {}
        form = BudgetAdminModelForm(data={'add_new_amount': 200})
        self.assertRaises(
            PermissionError,
            self.budgetAdmin.save_model,
            CurrentRequest(user=self.not_superuser),
            budget_obj,
            form,
            None,
        )

    # test superuser save with budget
    def test_save_model_save_created_by_field(self):
        budget_obj = Budget(disburser=AdminUserFactory())
        form = BudgetAdminModelForm(data={'add_new_amount': 200})
        self.assertEqual(form.is_valid(), True)
        self.budgetAdmin.save_model(
            CurrentRequest(user=self.superuser), budget_obj, form, None
        )
        self.assertEqual(budget_obj.created_by, self.superuser)
