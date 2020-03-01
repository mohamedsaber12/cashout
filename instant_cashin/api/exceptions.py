import logging

from django.utils.translation import gettext as _

from rest_framework.views import exception_handler

from data.utils import get_client_ip

from ..utils import logging_message


INSTANT_CASHIN_REQUEST_LOGGER = logging.getLogger("instant_cashin_requests")


def custom_exception_handler(exc, context):
    """
    Returns the response that should be used for any given exception in a custom manner.

    By default we handle the REST framework `APIException`, and also
    Django's built-in `Http404` and `PermissionDenied` exceptions.

    Any unhandled exceptions may return `None`, which will cause a 500 error
    to be raised.
    """
    response = exception_handler(exc, context)

    if response is not None:
        if response.data.get("detail"):
            response.data["disbursement_status"] = _("failed")
            response.data["status_description"] = response.data.pop("detail")

        if response.data.get("status_code", None) is None:
            response.data["status_code"] = str(response.status_code)

    logging_message(
            INSTANT_CASHIN_REQUEST_LOGGER, "[Request Data - API EXCEPTION]",
            f"{context['view'].request.method}: {context['view'].request.path}, "
            f"from Ip Address: {get_client_ip(context['view'].request)}\n\t"
            f"Data dictionary: {context['view'].request.data}"
    )

    return response
