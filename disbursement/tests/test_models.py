# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from disbursement.models import (Agent, DisbursementDocData, DisbursementData,
                                 BankTransaction)
from users.models import User
from data.models import Doc


class AgentModelTests(TestCase):

    def setUp(self):
        self.root = User(id=1, username='test_root_user')
        self.root.root = self.root
        self.root.save()

    # test create agent
    def test_create_agent(self):
        agent = Agent(msisdn='01021469732', wallet_provider=self.root)
        self.assertEqual(agent.__str__(), 'Agent 01021469732 for Root: test_root_user')

    # test create super agent
    def test_create_super_agent(self):
        agent = Agent(msisdn='01021469732', wallet_provider=self.root, super=True)
        self.assertEqual(agent.__str__(), 'SuperAgent 01021469732 for Root: test_root_user')


class DisbursementDocDataModelTests(TestCase):
    def setUp(self):
        self.doc = Doc()
        self.disbursement_doc_data = DisbursementDocData(doc=self.doc, txn_id='uygdsdxvbcxddsghh')

    # test create DisbursementDocData
    def test_create_disbursement_doc_data(self):
        self.assertEqual(
            self.disbursement_doc_data.__str__(),
            f"uygdsdxvbcxddsghh -- {self.doc.id}")

    # test DisbursementDocData status
    def test_disbursement_doc_data_status(self):
        self.disbursement_doc_data.doc_status = DisbursementDocData.PROCESSED_SUCCESSFULLY
        self.assertEqual(
                self.disbursement_doc_data.doc_status,
                DisbursementDocData.PROCESSED_SUCCESSFULLY)


class DisbursementDataModelTests(TestCase):
    def setUp(self):
        self.doc = Doc()
        self.disbursement_data = DisbursementData(doc=self.doc, msisdn='01021469732')

    # test create DisbursementDocData
    def test_create_disbursement_doc_data(self):
        self.assertEqual(self.disbursement_data.__str__(), "01021469732")

    # test disburse status fails in DisbursementDocData model
    def test_get_is_disbursed_failed(self):
        self.assertEqual(self.disbursement_data.get_is_disbursed, "Failed")

    # test disburse status success in DisbursementDocData model
    def test_get_is_disbursed_success(self):
        self.disbursement_data.is_disbursed = True
        self.assertEqual(self.disbursement_data.get_is_disbursed, "Successful")

class BankTransactionModelTests(TestCase):
    def setUp(self):
        self.bank_transaction = BankTransaction()

    # test create Bank Transaction
    def test_create_bank_Transaction(self):
        self.assertEqual(self.bank_transaction.__str__(), str(self.bank_transaction.transaction_id))
