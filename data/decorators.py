from __future__ import absolute_import, division, print_function, unicode_literals

from django.contrib.auth.decorators import user_passes_test

from django_otp import user_has_device
from django_otp.conf import settings
from django.utils import translation
from django.utils.functional import wraps

#http://django-otp.readthedocs.io/en/latest/auth/
def otp_required(view=None, redirect_field_name='next', login_url=None, if_configured=False):
    """
    Similar to :func:`~django.contrib.auth.decorators.login_required`, but
    requires the user to be :term:`verified`. By default, this redirects users
    to :setting:`OTP_LOGIN_URL`.

    :param if_configured: If ``True``, an authenticated user with no confirmed
        OTP devices will be allowed. Default is ``False``.
    :type if_configured: bool
    """
    if login_url is None:
        login_url = settings.OTP_LOGIN_URL

    def test(user):
        if not user.can_disburse:
            return True
        return user.is_verified() or (if_configured and user.is_authenticated and not user_has_device(user))

    decorator = user_passes_test(test, login_url=login_url, redirect_field_name=redirect_field_name)

    return decorator if (view is None) else decorator(view)



def respects_language(func):
    '''
    Decorator for tasks with respect to site's current language.
    You can use in tasks.py 
    Be sure that task method have kwargs argument:

        @task
        @respects_language
        def my_task(**kwargs):
            pass

    You can call this task this way:

        from django.utils import translation
        tasks.my_task.delay(language=translation.get_language())
    '''
    def wrapper(*args, **kwargs):
        language = kwargs.pop('language', None)
        prev_language = translation.get_language()
        language and translation.activate(language)
        try:
            return func(*args, **kwargs)
        finally:
            translation.activate(prev_language)

    wrapper.__doc__ = func.__doc__
    wrapper.__name__ = func.__name__
    wrapper.__module__ = func.__module__
    
    return wraps(func)(wrapper)
