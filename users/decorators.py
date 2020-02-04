from django.shortcuts import resolve_url
from django.core.exceptions import PermissionDenied
from django.conf import settings
from urllib.parse import urlparse
from functools import wraps
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse


def user_passes_test_with_request(test_func, login_url=None, 
        redirect_field_name=REDIRECT_FIELD_NAME, handle_login_url=None):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.'

    @param handle_login_url:function that takes request as param and return login_url.
    """
    
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request):
                return view_func(request, *args, **kwargs)
            path = request.build_absolute_uri()
            new_login_url = None
            if handle_login_url:
                new_login_url  = handle_login_url(request)
            
            resolved_login_url = resolve_url(new_login_url or login_url or settings.LOGIN_URL)
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


def setup_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    """
    checks if root user finished setup and can access the view or not
    """
    def root_can_pass(request):
        user = request.user
        status = request.user.get_status(request)

        if not user.is_root:
            return True
        if status == 'disbursement' and user.can_pass_disbursement:
            return True
        if status == 'collection' and user.can_pass_collection:
            return True
        return False

    def handle_login_url(request):
        status = request.user.get_status(request)
        if status == 'collection':
            login_url = reverse('users:setting-collection-collectiondata')
        elif status == 'disbursement':
            login_url = reverse('users:setting-disbursement-pin')
        else:
            login_url = reverse('users:redirect')
        return login_url    

    actual_decorator = user_passes_test_with_request(
        root_can_pass,
        login_url=login_url,
        redirect_field_name=redirect_field_name,
        handle_login_url=handle_login_url
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def collection_users(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url='/'):
    """
    collection users only allowed
    """
    def can_pass(request):
        user = request.user
        status = request.user.get_status(request)
        return user.is_uploader or ( (user.is_root or user.is_upmaker) and status == 'collection')

    actual_decorator = user_passes_test_with_request(
        can_pass,
        login_url=login_url,
        redirect_field_name=None
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def root_or_maker_or_uploader(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url='/'):
    """
    root and maker and uploader only allowed
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_maker or u.is_root or u.is_uploader or u.is_upmaker,
        login_url=login_url,
        redirect_field_name=None
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def disbursement_users(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url='/'):
    """
    disbursement_users only allowed
    """
    def can_pass(request):
        user = request.user
        status = request.user.get_status(request)
        return user.is_maker or user.is_checker or ((user.is_root or user.is_upmaker) and status == 'disbursement')
    
    actual_decorator = user_passes_test_with_request(
        can_pass,
        login_url=login_url,
        redirect_field_name=None
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def root_or_superadmin(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url='/'):
    """
    root and super admin only allowed
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_root or u.is_superadmin,
        login_url=login_url,
        redirect_field_name=None
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def root_only(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url='/'):
    """
    root only allowed
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_root,
        login_url=login_url,
        redirect_field_name=None
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def maker_only(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url='/'):
    """
    makers only allowed
    """
    def can_pass(request):
        user = request.user
        status = request.user.get_status(request)
        return user.is_maker or ( user.is_upmaker and status == 'disbursement')

    actual_decorator = user_passes_test_with_request(
        can_pass,
        login_url=login_url,
        redirect_field_name=None
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
