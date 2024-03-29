# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import OrderedDict
import uuid

from django.core.validators import MaxLengthValidator, MinLengthValidator

from rest_framework import serializers

from .. import utils


class CustomChoicesField(serializers.Field):
    """
    Custom ChoiceField serializer field
    """

    def __init__(self, choices, **kwargs):
        """init."""
        self._choices = OrderedDict(choices)
        super().__init__(**kwargs)

    def to_representation(self, obj):
        """Used while retrieving value for the field."""
        return self._choices[obj].lower()

    def to_internal_value(self, data):
        """Used while storing value for the field."""
        for i in self._choices:
            if self._choices[i] == data:
                return i
        raise serializers.ValidationError("Acceptable values are {0}.".format(list(self._choices.values())))


class UUIDListField(serializers.ListField):
    """
    UUID list serializer field
    """

    child = serializers.UUIDField(default=uuid.uuid4())


class CustomMinLengthValidator(MinLengthValidator):
    """
    Customized min length validator for validating&escaping chars from bank account/card numbers
    """

    def clean(self, x):
        return len(utils.get_digits(x))


class CustomMaxLengthValidator(MaxLengthValidator):
    """
    Customized max length validator for validating&escaping chars from bank account/card numbers
    """

    def clean(self, x):
        return len(utils.get_digits(x))


class CardNumberField(serializers.CharField):
    """
    Form field for validating and accepting bank accounts/cards
    """

    default_validators = [
        CustomMinLengthValidator(6),
        CustomMaxLengthValidator(29),
    ]
