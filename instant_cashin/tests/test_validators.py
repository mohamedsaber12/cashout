# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from instant_cashin.api.validators import (
    issuer_validator, fees_validator, cashin_issuer_validator,
    bank_code_validator, bank_transaction_type_validator
)

class ValidatorsTests(TestCase):

    def test_issuer_validator(self):
        self.assertRaises(
            ValidationError,
            issuer_validator,
            "fake issuer"
        )

    def test_fees_validator(self):
        self.assertRaises(
            ValidationError,
            fees_validator,
            "fake fees"
        )

    def test_cashin_issuer_validator(self):
        self.assertRaises(
            ValidationError,
            cashin_issuer_validator,
            "fake issuer"
        )

    def test_bank_code_validator(self):
        self.assertRaises(
            ValidationError,
            bank_code_validator,
            "fake bank code"
        )

    def test_bank_transaction_type_validator(self):
        self.assertRaises(
            ValidationError,
            bank_transaction_type_validator,
            "fake transaction type"
        )