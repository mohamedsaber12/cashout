# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
from instant_cashin.models import AmanTransaction, InstantTransaction

class AmanTransactionTests(TestCase):
    def setUp(self):
        self.instant_trx = InstantTransaction()
        self.aman_trx_obj = AmanTransaction(transaction=self.instant_trx)

    # test Aman Transaction object created successfully
    def test_aman_transaction_created_successfully(self):
        self.assertEqual(
            self.aman_trx_obj.__str__(),
            self.instant_trx.__str__()
        )