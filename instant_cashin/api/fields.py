# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import OrderedDict
import uuid

from rest_framework import serializers


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
        return self._choices[obj]

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
