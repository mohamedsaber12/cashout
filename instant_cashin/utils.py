from django.utils.translation import gettext_lazy as _

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


def get_corresponding_env_url(vmt_obj):
    """
    This function will get the corresponding vmt environment url from the .env file
    :param vmt_obj: vmt credentials of the user being hit the request
    """
    environment_url = get_dot_env()
    return environment_url.str(vmt_obj.vmt_environment)
