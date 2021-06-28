# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
from rest_framework import status

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


class InstantTransactionTests(TestCase):
    def setUp(self):
        self.instant_trx = InstantTransaction()

    # test update_status_code_and_description method
    def test_update_status_code_and_description(self):
        self.instant_trx.update_status_code_and_description()
        self.assertEqual(
            self.instant_trx.transaction_status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        self.assertEqual(
            self.instant_trx.transaction_status_description,
            ""
        )

    # test mark instant transaction as pending
    def test_mark_pending(self):
        self.instant_trx.mark_pending()
        self.assertEqual(
            self.instant_trx.status,
            InstantTransaction.PENDING
        )

    # test mark instant transaction as failed
    def test_mark_failed(self):
        self.instant_trx.mark_failed()
        self.assertEqual(
            self.instant_trx.status,
            InstantTransaction.FAILED
        )

    # test mark instant transaction as SUCCESSFUL
    def test_mark_successful(self):
        self.instant_trx.mark_successful()
        self.assertEqual(
            self.instant_trx.status,
            InstantTransaction.SUCCESSFUL
        )

    # test aman_transaction is None
    def test_aman_transaction_not_exist(self):
        self.assertRaises(
            AttributeError,
            self.instant_trx.aman_transaction,
        )

    # test aman_transaction
    def test_aman_transaction(self):
        self.aman_trx_obj = AmanTransaction(transaction=self.instant_trx)
        self.aman_trx_obj.save()
        self.assertEqual(
            self.instant_trx.aman_transaction,
            self.aman_trx_obj
        )

    # test issuer_choice_verbose
    def test_issuer_choice_verbose(self):
        self.instant_trx.issuer_type = self.instant_trx.VODAFONE
        self.assertEqual(
            self.instant_trx.issuer_choice_verbose,
            "Vodafone"
        )

    # test status_choice_verbose
    def test_status_choice_verbose(self):
        self.assertEqual(
            self.instant_trx.status_choice_verbose,
            "Default"
        )