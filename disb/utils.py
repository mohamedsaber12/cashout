import logging

from django.contrib import admin
from django.utils.translation import gettext as _


BUDGET_LOGGER = logging.getLogger("custom_budgets")


def logging_message(logger, head, user, message):
    """
    Simple function that will take the logger and the message and log them in
    :param logger: the logger itself that will handle the log message
    :param head: the head/title of the log message
    :param user: the user being stored at the request
    :param message: the message that will be logged
    :return: The message will be logged into the specified logger
    """
    return logger.debug(_(f"{head}\n\tUser: {user}\n\t{message}"))


def custom_budget_logger(disburser, total_disbursed_amount, user="Anonymous", another_message="", head=""):
    """
    logger function to be used at any custom budget logging
    """
    if not head:
        head = "[CUSTOM BUDGET - MANUAL PATCH]"

    return logging_message(
            logger=BUDGET_LOGGER, head=head,
            user=f"{user} -- Root/Disburser: {disburser}",
            message=f"{total_disbursed_amount}{another_message}"
    )


def custom_titled_filter(title):
    """
    Function for changing field's filter title at the django admin
    :param title: the new title to be viewed
    """
    class Wrapper(admin.FieldListFilter):
        def __new__(cls, *args, **kwargs):
            instance = admin.FieldListFilter.create(*args, **kwargs)
            instance.title = title
            return instance
    return Wrapper
