# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from disbursement.utils import (determine_trx_category_and_purpose,
                                determine_transaction_type,
                                get_error_description_from_error_code)

class UtilsTests(TestCase):

    # test determine transaction category and purpose for transaction type => MOBILE
    def test_determine_trx_category_and_purpose_for_mobile(self):
        self.category_purpose_dict = determine_trx_category_and_purpose('MOBILE')
        self.assertEqual(self.category_purpose_dict['category_code'], 'MOBI')
        self.assertEqual(self.category_purpose_dict['purpose'], 'CASH')

    # test determine transaction category and purpose for transaction type => SALARY
    def test_determine_trx_category_and_purpose_for_salary(self):
        self.category_purpose_dict = determine_trx_category_and_purpose('SALARY')
        self.assertEqual(self.category_purpose_dict['category_code'], 'CASH')
        self.assertEqual(self.category_purpose_dict['purpose'], 'SALA')

    # test determine transaction category and purpose for transaction type => PREPAID_CARD
    def test_determine_trx_category_and_purpose_for_prepaid_card(self):
        self.category_purpose_dict = determine_trx_category_and_purpose('PREPAID_CARD')
        self.assertEqual(self.category_purpose_dict['category_code'], 'PCRD')
        self.assertEqual(self.category_purpose_dict['purpose'], 'CASH')

    # test determine transaction category and purpose for transaction type => CREDIT_CARD
    def test_determine_trx_category_and_purpose_for_credit_card(self):
        self.category_purpose_dict = determine_trx_category_and_purpose('CREDIT_CARD')
        self.assertEqual(self.category_purpose_dict['category_code'], 'CASH')
        self.assertEqual(self.category_purpose_dict['purpose'], 'CCRD')

    # test determine transaction category and purpose for transaction type => different_value
    def test_determine_trx_category_and_purpose_for_unknown_type(self):
        self.category_purpose_dict = determine_trx_category_and_purpose('')
        self.assertEqual(self.category_purpose_dict['category_code'], 'CASH')
        self.assertEqual(self.category_purpose_dict['purpose'], 'CASH')

    # test determine transaction type based on transaction category code and purpose
    def test_determine_transaction_type_is_salary(self):
        self.transaction_type = determine_transaction_type('CASH', 'SALA')
        self.assertEqual(self.transaction_type, 'salary')

    # test determine transaction type based on transaction category code and purpose
    def test_determine_transaction_type_is_prepaid_card(self):
        self.transaction_type = determine_transaction_type('PCRD', 'CASH')
        self.assertEqual(self.transaction_type, 'prepaid_card')

    # test determine transaction type based on transaction category code and purpose
    def test_determine_transaction_type_credit_card(self):
        self.transaction_type = determine_transaction_type('CASH', 'CCRD')
        self.assertEqual(self.transaction_type, 'credit_card')

    # test determine transaction type based on transaction category code and purpose
    def test_determine_transaction_type_is_cash_transfer(self):
        self.transaction_type = determine_transaction_type('CASH', 'CASH')
        self.assertEqual(self.transaction_type, 'cash_transfer')

    # test get error description from error code => 403
    def test_get_error_description_from_error_code(self):
        self.error_description = get_error_description_from_error_code('403')
        self.assertEqual(self.error_description, 'Channel authentication failed')

    # test get error description from error code => SUCCESS
    def test_get_error_description_from_error_code_is_success(self):
        self.error_description = get_error_description_from_error_code('SUCCESS')
        self.assertEqual(self.error_description, 'Success')

    # test get error description from error code => unknown code. ex:- (1234)
    def test_get_error_description_from_error_code_is_unknown_code(self):
        self.error_description = get_error_description_from_error_code('1234')
        self.assertEqual(self.error_description, 'External error, please contact your support team for further details')