# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _


class NumberValidator:
    """
    Custom password validator to check for specific digits length
    """

    def __init__(self, min_digits=0):
        self.min_digits = min_digits

    def validate(self, password, user=None):
        if not len(re.findall('\d', password)) >= self.min_digits:
            raise ValidationError(
                    _(f'The password must contain at least {self.min_digits} digit(s), 0-9.'), code='password_no_number'
            )

    def get_help_text(self):
        return _(f'Your password must contain at least {self.min_digits} digit(s), 0-9.')


class UppercaseValidator:
    """
    Custom password validator to check for specific upper case characters length
    """

    def __init__(self, min_chars=0):
        self.min_chars = min_chars

    def validate(self, password, user=None):
        if not len(re.findall('[A-Z]', password)) >= self.min_chars:
            raise ValidationError(
                    _(f'The password must contain at least {self.min_chars} uppercase letter(s), A-Z.'),
                    code='password_no_upper',
            )

    def get_help_text(self):
        return _(f'Your password must contain at least {self.min_chars} uppercase letter(s), A-Z.')


class LowercaseValidator:
    """
    Custom password validator to check for specific lower case characters length
    """

    def __init__(self, min_chars=0):
        self.min_chars = min_chars

    def validate(self, password, user=None):
        if not len(re.findall('[a-z]', password)) >= self.min_chars:
            raise ValidationError(
                    _(f'The password must contain at least {self.min_chars} lowercase letter(s), a-z.'),
                    code='password_no_lower',
            )

    def get_help_text(self):
        return _(f'Your password must contain at least {self.min_chars} lowercase letter(s), a-z.')


class SymbolValidator:
    """
    Custom password validator to check for specific symbols length
    """

    def validate(self, password, user=None):
        if not re.findall('[()[\]{}|\\`~!@#$%^&*_\-+=;:\'",<>./?]', password):
            raise ValidationError(
                    _("The password must contain at least 1 symbol: ()[]{}|\`~!@#$%^&*_-+=;:'\",<>./?"),
                    code='password_no_symbol',
            )

    def get_help_text(self):
        return _("Your password must contain at least 1 symbol: ()[]{}|\`~!@#$%^&*_-+=;:'\",<>./?")


def ComplexPasswordValidator(password, user=None):
    if re.match("^[a-zA-Z0-9_]*$", password):
        raise ValidationError(
            _("This password must contain a special character."),
            code='password_does_not_contain_a_special_character',
        )
    if not(any(x.isupper() for x in password)):
        raise ValidationError(
            _("This password must contain an upper case letter."),
            code='password_does_not_contain_an_upper_character',
        )
    if not(any(x.islower() for x in password)):
        raise ValidationError(
            _("This password must contain a lower case letter."),
            code='password_does_not_contain_a_lower_character',
        )
    if not(any(x.isdigit() for x in password)):
        raise ValidationError(
            _("This password must contain a digit."),
            code='password_does_not_contain_a_digit',
        )


def get_help_text():
    return _("Your password must contain an upper case letter, a lower case letter, a special character, and a digit.")
