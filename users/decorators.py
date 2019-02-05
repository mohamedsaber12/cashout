from django.shortcuts import resolve_url
from django.core.exceptions import PermissionDenied
from django.conf import settings
from urllib.parse import urlparse
from functools import wraps
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse


def user_passes_test_with_request(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request):
                return view_func(request, *args, **kwargs)
            path = request.build_absolute_uri()
            resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)
            # If the login url is the same scheme and net location then just
            # use the path as the "next" url.
            login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
            current_scheme, current_netloc = urlparse(path)[:2]
            if ((not login_scheme or login_scheme == current_scheme) and
                    (not login_netloc or login_netloc == current_netloc)):
                path = request.get_full_path()
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(
                path, resolved_login_url, redirect_field_name)
        return _wrapped_view
    return decorator


def setup_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url='/settings/up/'):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    def root_can_pass(request):
        user = request.user
        
        if not user.is_root:
            return True
        status = request.COOKIES.get('status')
        if status == 'disbursement' and user.can_pass_disbursement:
            return True
        if status == 'collection' and user.can_pass_collection:
            return True
        return False

    actual_decorator = user_passes_test_with_request(
        root_can_pass,
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
