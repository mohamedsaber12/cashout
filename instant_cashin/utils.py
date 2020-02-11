from django.utils.translation import gettext_lazy as _
from environ import ImproperlyConfigured

from payouts.utils import get_dot_env


def logging_message(logger, head, message):
    """
    Simple function that will take the logger and the message and log them in
    :param logger: the logger itself that will handle the log message
    :param head: the head/title of the log message
    :param message: the message that will be logged
    :return: The message will be logged into the specified logger
    """
    return logger.debug(_(f"{head}\n\t{message}"))


def get_from_env(key):
    """
    This function will get the corresponding key from the .env file
    """
    environment_vars_dict = get_dot_env()

    if not environment_vars_dict.str(key):
        raise ImproperlyConfigured(f"{key} does not exist at your .env file")

    return environment_vars_dict.str(key)
