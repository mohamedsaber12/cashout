from environ import ImproperlyConfigured

from django.utils.translation import gettext_lazy as _

from rest_framework.response import Response

from data.utils import get_client_ip

from payouts.utils import get_dot_env


def logging_message(logger, head, request, message):
    """
    Simple function that will take the logger and the message and log them in
    :param logger: the logger itself that will handle the log message
    :param head: the head/title of the log message
    :param request: the pure http request object
    :param message: the message that will be logged
    :return: The message will be logged into the specified logger
    """
    return logger.debug(_(f"{head}\nUser: {request.user} -- Ip Address: {get_client_ip(request)}\n{message}"))


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
