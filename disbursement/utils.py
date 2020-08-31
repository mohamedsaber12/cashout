# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.utils.translation import gettext as _


def logging_message(logger, head, user, message):
    """
    Simple function that will take the logger and the message and log them in
    :param logger: the logger itself that will handle the log message
    :param head: the head/title of the log message
    :param user: the user being stored at the request
    :param message: the message that will be logged
    :return: The message will be logged into the specified logger
    """
    return logger.debug(_(f"{head}\nUser: {user}\n{message}"))


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
