# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import gettext_lazy as _


def logging_message(logger, head, request, message):
    """
    Simple function that will take the logger and the message and log them in
    :param logger: the logger itself that will handle the log message
    :param head: the head/title of the log message
    :param request: the pure http request object
    :param message: the message that will be logged
    :return: The message will be logged into the specified logger
    """
    return logger.debug(_(f"{head} [{request.user}] -- {message}"))
