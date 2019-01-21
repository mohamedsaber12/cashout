from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse


def setup_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url='/settings/up/'):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.can_pass if u.is_root else True,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def maker_only(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url='/'):
    """
    Decorator for views that checks that the user is maker, redirecting
    to '/' if not.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_maker,
        login_url=login_url,
        redirect_field_name=None
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
