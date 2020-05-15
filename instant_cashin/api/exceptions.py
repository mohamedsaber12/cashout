import logging

from django.utils.translation import gettext as _

from rest_framework.views import exception_handler

from utilities.logging import logging_message


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
        exception_code = exc.default_code

        # Not Authenticated custom response field
        if exception_code == "not_authenticated":
            response.data["disbursement_status"] = _("failed")

        if response.data.get("status_code", None) is None:
            response.data["status_code"] = str(response.status_code)

        if response.data.get("detail", None) is None:
            response.data["status_description"] = response.data.pop("detail")

        common_logging_msg = f"{context['view'].request.method}: {context['view'].request.path}" \
                             f" -- exception reason: {exception_code}\n"

        try:
            request_data = context['view'].request.data
            logging_message(
                    INSTANT_CASHIN_REQUEST_LOGGER, "[API EXCEPTION]", context['view'].request,
                    f"{common_logging_msg}Data dictionary: {request_data}"
            )
        except Exception as error:
            INSTANT_CASHIN_REQUEST_LOGGER.exception(
                    f"[Request Data - API EXCEPTION]\n{common_logging_msg}Exception: {error}"
            )

    return response
