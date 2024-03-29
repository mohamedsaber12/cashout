from environ import ImproperlyConfigured
import re

from rest_framework.response import Response

from payouts.utils import get_dot_env


re_non_digits = re.compile(r'[^\d]+')


def get_from_env(key):
    """
    This function will get the corresponding key from the .env file
    """
    environment_vars_dict = get_dot_env()

    if not environment_vars_dict.str(key):
        raise ImproperlyConfigured(f"{key} does not exist at your .env file")

    return environment_vars_dict.str(key)


def default_response_structure(transaction_id="0",
                               disbursement_status="failed",
                               status_description="",
                               field_status_code=None,
                               response_status_code=None):
    """
    This function uniforms the response's body structure
    :param transaction_id: id of the currently processed transaction
    :param disbursement_status: failed or success, default is failed
    :param status_description: failure reason if any
    :param field_status_code: status code returned as a string field within the response body
    :param response_status_code: the response's status code returned at the response header
    :return:
    """
    if not field_status_code:
        field_status_code = response_status_code

    if not response_status_code:
        response_status_code = field_status_code

    return Response(
            {
                "transaction_id": transaction_id,
                "disbursement_status": disbursement_status,
                "status_description": status_description,
                "status_code": str(field_status_code)
            },
            status=response_status_code
    )


def get_digits(value):
    """
    Get all digits from input string.

    :type value: str
    :rtype: str
    """
    if not value:
        return ''
    return re_non_digits.sub('', str(value))
