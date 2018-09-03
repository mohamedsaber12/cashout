from django.core.exceptions import ValidationError
import re



def ComplexPasswordValidator(password, user=None):
    if re.match("^[a-zA-Z0-9_]*$", password):
        raise ValidationError(
            "This password must contain a special character.",
            code='password_does_not_contain_a_special_character',
        )
    if not(any(x.isupper() for x in password)):
        raise ValidationError(
            "This password must contain an upper case letter.",
            code='password_does_not_contain_an_upper_character',
        )
    if not(any(x.islower() for x in password)):
        raise ValidationError(
            "This password must contain a lower case letter.",
            code='password_does_not_contain_a_lower_character',
        )
    if not(any(x.isdigit() for x in password)):
        raise ValidationError(
            "This password must contain a digit.",
            code='password_does_not_contain_a_digit',
        )


def get_help_text():
    return "Your password must contain an upper case letter, a lower case letter, a special character, and a digit."
