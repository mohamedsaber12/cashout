import re

from django.conf import settings
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib.auth import logout

EXEMPT_URLS = [re.compile(settings.LOGIN_URL.lstrip('/'))]
if hasattr(settings, 'LOGIN_EXEMPT_URLS'):
    EXEMPT_URLS += [re.compile(url) for url in settings.LOGIN_EXEMPT_URLS]

ALLOWED_URLS_FOR_ADMIN = (
    re.compile(r'^client*'),
    re.compile(r'^profile*')
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
            logout(request)
        if request.user.is_authenticated:
            if request.user.is_superadmin:
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
