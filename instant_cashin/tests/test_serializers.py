from rest_framework.test import APITestCase
from instant_cashin.api.serializers import InstantDisbursementRequestSerializer


class InstantDisbursementRequestSerializerTests(APITestCase):

    def test_serializer_msisdn_validation(self):
        data = {
            "issuer": "vodafone",
            "amount": 100
        }
        serializer = InstantDisbursementRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['non_field_errors'],
            ["You must pass valid msisdn"]
        )

    def test_serializer_email_validation(self):
        data = {
            "issuer": "aman",
            "amount": 100
        }
        serializer = InstantDisbursementRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['non_field_errors'],
            ["You must pass valid values for fields [first_name, last_name, email]"]
        )

    def test_serializer_bank_card_number_validation(self):
        data = {
            "issuer": "bank_card",
            "amount": 100
        }
        serializer = InstantDisbursementRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['non_field_errors'],
            ["You must pass valid values for fields [bank_code, bank_card_number, bank_transaction_type, full_name]"]
        )

    def test_serializer_full_name_validation(self):
        data = {
            "issuer": "orange",
            "amount": 100
        }
        serializer = InstantDisbursementRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['non_field_errors'],
            ["You must pass valid value for field msisdn"]
        )
      

    def test_serializer_full_name_have_special_character(self):
        data = {
            "issuer": "bank_card",
            "amount": 100,
            "full_name": "%!",
            "bank_card_number": "1111-2222-3333-4444",
            "bank_code": "CIB",
            "bank_transaction_type": "cash_transfer"
        }
        serializer = InstantDisbursementRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['non_field_errors'],
            ["Symbols like !%*+&,<=> not allowed in full_name"]
        )