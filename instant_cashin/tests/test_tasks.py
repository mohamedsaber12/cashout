# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from instant_cashin.tasks import check_for_status_updates_for_latest_bank_transactions


class StatusUpdatesForLatestBankTransactionsTests(TestCase):


    def test_check_for_status_updates_for_latest_bank_transactions(self):
        self.assertTrue(check_for_status_updates_for_latest_bank_transactions())
