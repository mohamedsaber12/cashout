import re
from importlib import import_module

from django.conf import settings
from django.urls import reverse
from django.shortcuts import redirect
from django_otp import user_has_device

from .models import Visitor
from .views import ourlogout


engine = import_module(settings.SESSION_ENGINE)

EXEMPT_URLS = [re.compile(settings.LOGIN_URL.lstrip('/'))]
if hasattr(settings, 'LOGIN_EXEMPT_URLS'):
    EXEMPT_URLS += [re.compile(url) for url in settings.LOGIN_EXEMPT_URLS]

ALLOWED_URLS_FOR_ADMIN = (
    re.compile(r'^client*'),
    re.compile(r'^support*'),
    re.compile(r'^profile*'),
    re.compile(r'^agent/budget/edit/*'),
    re.compile(r'^agent/balance-inquiry/*'),
    re.compile(reverse('users:entity_branding').lstrip('/')),
    re.compile(reverse('users:delete').lstrip('/')),
    re.compile(settings.MEDIA_URL.lstrip('/')),
    re.compile(reverse('set_language').lstrip('/'))
)


class EntitySetupCompletionMiddleWare:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        assert hasattr(request, 'user')
        path = request.path_info.lstrip('/')
        url_is_exempt = any(url.match(path) for url in EXEMPT_URLS)
        url_is_allowed = any(url.match(path) for url in ALLOWED_URLS_FOR_ADMIN)
        if path == reverse('users:logout').lstrip('/'):
            ourlogout(request)
        if request.user.is_authenticated:
            if request.user.is_superadmin and not request.user.is_superuser:
                if re.compile(r"client/delete/*").match(path) :
                    return None
                if request.user.has_uncomplete_entity_creation():
                    entity_creation = request.user.uncomplete_entity_creation()
                    path = entity_creation.get_reverse()
                    if path == request.path:
                        return None
                    return redirect(entity_creation.get_reverse())
                if url_is_exempt or url_is_allowed:
                    return None
                return redirect(reverse("users:clients"))
        else:
            if url_is_exempt:
                return None
            return redirect(settings.LOGIN_URL)


class CheckerTwoFactorAuthMiddleWare:
    """
    Force checkers to do two factor authentication once per device.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        path = request.path_info
        two_factor_base_url = 'account/two_factor/'
        media_path = settings.MEDIA_URL
        is_media_path = True if media_path in path and f'{media_path}documents/' not in path else False
        urls = [
            reverse("two_factor:profile"),
            reverse("users:otp_login"),
            reverse("two_factor:setup"),
            '/account/two_factor/qrcode/',
            reverse("set_language")
        ]
        
        if request.user.is_authenticated and request.user.is_checker and not is_media_path:
            is_verified = request.user.is_verified() or request.user.is_totp_verified
            if two_factor_base_url in path and is_verified:
                return redirect(reverse("data:main_view"))            
            if not request.user.is_totp_verified and user_has_device(request.user) and (not path in urls or path == reverse("two_factor:profile")):
                return redirect(reverse("users:otp_login"))
            if not is_verified and not path in urls:
                return redirect(reverse("two_factor:profile"))
            

class PreventConcurrentLoginsMiddleware:
    """
    Django middleware that prevents multiple concurrent logins..
    Adapted from http://stackoverflow.com/a/1814797 and https://gist.github.com/peterdemin/5829440
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.user.is_authenticated:
            key_from_cookie = request.session.session_key
            if hasattr(request.user, 'visitor'):
                session_key_in_visitor_db = request.user.visitor.session_key
                if session_key_in_visitor_db != key_from_cookie:
                    # Delete the Session object from database and cache
                    engine.SessionStore(session_key_in_visitor_db).delete()
                    request.user.visitor.session_key = key_from_cookie
                    request.user.visitor.save()
            else:
                Visitor.objects.create(
                    user=request.user,
                    session_key=key_from_cookie
                )
