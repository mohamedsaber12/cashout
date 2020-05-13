import logging

from django.conf import settings
from django_otp import _user_is_authenticated, user_has_device

from rest_framework import permissions


DATA_LOGGER = logging.getLogger("disburse")


class TOTPAuthenticated(permissions.IsAuthenticated):
    """
    Allows access only to TOTP authenticated users.
    """

    def has_permission(self, request, view):
        is_authenticated = super(TOTPAuthenticated, self).has_permission(request=request, view=view)

        def test(user):
            return user.is_verified() or (_user_is_authenticated(user) and not user_has_device(user))

        return test(request.user) and is_authenticated


class BlacklistPermission(permissions.BasePermission):
    """
    Global permission check for whitelisted IPs.
    """

    def has_permission(self, request, view):
        ip_addr = request.META['REMOTE_ADDR']
        DATA_LOGGER.debug("[CAN DISBURSE]" + f" Ip Address: {str(ip_addr)}")
        if ip_addr in settings.ALLOWED_HOSTS:
            return True
        else:
            return False
