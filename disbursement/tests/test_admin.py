# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from disbursement.admin import (BankTransactionAdminModel, DistinctFilter,
                                VMTDataAdmin, DisbursementDataAdmin)
from disbursement.models import (BankTransaction, VMTData, DisbursementData,
                                 DisbursementDocData)
from users.models import User, RootUser
from data.models import Doc

class CurrentRequest(object):
    def __init__(self, user=None):
        self.user=user


class DistinctFilterTest(TestCase):
    def setUp(self):
        self.distinctFilter = DistinctFilter(CurrentRequest, {}, BankTransaction, BankTransactionAdminModel)
    # test lookups for distinct filter
    def test_lookups(self):
        self.assertEqual(self.distinctFilter.lookups(
            CurrentRequest, BankTransactionAdminModel), (('distinct', 'Distinct'),))

class BankTransactionAdminModelTest(TestCase):

    def setUp(self):
        self.bankTransactionAdmin = BankTransactionAdminModel(
            model=BankTransaction, admin_site=AdminSite()
        )
    # check if bank transaction admin model has add permission
    def test_has_add_permission(self):
        self.assertEqual(self.bankTransactionAdmin.has_add_permission(CurrentRequest), False)

    # check if bank transaction admin model has delete permission
    def test_has_delete_permission(self):
        self.assertEqual(self.bankTransactionAdmin.has_delete_permission(CurrentRequest), False)

    # check if bank transaction admin model has change permission
    def test_has_change_permission(self):
        self.assertEqual(self.bankTransactionAdmin.has_change_permission(CurrentRequest), False)


class DisbursementDataAdminTest(TestCase):
    def setUp(self):
        self.disbursementDataAdmin = DisbursementDataAdmin(
            model=DisbursementData, admin_site=AdminSite()
        )
        self.disbursement_data_obj = DisbursementData(amount=10, msisdn='01111451253')


    # test Add transaction id field renamed to Trx ID
    def test__trx_id(self):
        self.assertEqual(self.disbursementDataAdmin._trx_id(
            self.disbursement_data_obj), self.disbursement_data_obj.id)

    # test Link to the original disbursement document
    def test__disbursement_document(self):
        self.disbursement_data_obj.doc = Doc()
        self.disbursementDocData = DisbursementDocData(doc=self.disbursement_data_obj.doc)
        self.assertEqual(
            self.disbursementDataAdmin._disbursement_document(self.disbursement_data_obj),
            f"<a href='/secure-portal/disbursement/disbursementdocdata/" +
            f"{self.disbursement_data_obj.doc.disbursement_txn.id}/change/'>" +
            f"{self.disbursement_data_obj.doc.id}</a>"
        )



class VMTDataAdminTest(TestCase):

    def setUp(self):
        self.VMTDataAdmin = VMTDataAdmin(
                model=VMTData, admin_site=AdminSite()
        )
        self.super_user = User(username='test_super_user', is_superuser=True)
        self.not_super_user = RootUser(id=1, username='test_not_super_user')
        self.not_super_user.root = self.not_super_user
        self.vmtData = VMTData()


    # check if VMTData admin model has add permission for super user
    def test_has_add_permission_For_superuser(self):
        self.assertEqual(self.VMTDataAdmin.has_add_permission(
            CurrentRequest(user=self.super_user)), True)

    # check if VMTData admin model has add permission for not super user without vmt object
    def test_has_add_permission_For_not_superuser(self):
        self.assertEqual(self.VMTDataAdmin.has_add_permission(
                CurrentRequest(user=self.not_super_user)), False)

    # check if VMTData admin model has add permission for not super user with vmt object
    def test_has_add_permission_For_not_superuser_with_vmt(self):
        self.not_super_user.vmt = self.vmtData
        self.assertEqual(self.VMTDataAdmin.has_add_permission(
                CurrentRequest(user=self.not_super_user)), False)