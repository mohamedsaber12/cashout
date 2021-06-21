from django.test import TestCase

from core.models import (
    AbstractTimeStamp,
    AbstractBaseModel,
    AbstractBaseStatus,
    AbstractBaseModelNamed,
    AbstractBaseTransaction,
)


class TestAbstractModels(TestCase):
    def setUp(self):
        self.abstract_time_stamp_model = AbstractTimeStamp
        self.abstract_base_model = AbstractBaseModel
        self.abstract_base_status = AbstractBaseStatus
        self.abstract_base_model_named = AbstractBaseModelNamed
        self.abstract_base_transaction = AbstractBaseTransaction

    def test_abstract_time_stamp_model(self):
        self.assertTrue(self.abstract_time_stamp_model._meta.abstract)

    def test_abstract_time_stamp_model_fields(self):
        fields = sorted(["created_at", "updated_at"])
        self.assertEqual(
            sorted(
                [
                    field.name
                    for field in self.abstract_time_stamp_model._meta.get_fields()
                ]
            ),
            fields,
        )

    def test_abstract_base_model_fields(self):
        fields = sorted(["created_at", "updated_at", "uid"])
        self.assertEqual(
            sorted(
                [
                    field.name
                    for field in self.abstract_base_model._meta.get_fields()
                ]
            ),
            fields,
        )

    def test_abstract_base_model(self):
        self.assertTrue(self.abstract_base_model._meta.abstract)

    def test_abstract_base_model_status(self):
        self.assertTrue(self.abstract_base_status._meta.abstract)

    def test_abstract_base_transaction(self):
        self.assertTrue(self.abstract_base_transaction._meta.abstract)

    def test_abstract_base_status_fields(self):
        fields = sorted(["status"])
        self.assertEqual(
            sorted(
                [
                    field.name
                    for field in self.abstract_base_status._meta.get_fields()
                ]
            ),
            fields,
        )

    def test_abstract_base_model_named(self):
        self.assertTrue(self.abstract_base_model_named._meta.abstract)

    def test_abstract_base_model_name_str(self):
        model = self.abstract_base_model_named
        model.name = "Hello"
        self.assertTrue(model.__str__(self=model), "Hello")
