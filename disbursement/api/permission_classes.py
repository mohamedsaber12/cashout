import logging

from django.conf import settings
from django_otp import user_has_device

from rest_framework import permissions


DATA_LOGGER = logging.getLogger("disburse")


class TOTPAuthenticated(permissions.IsAuthenticated):
    """
    Allows access only to TOTP authenticated users.
    """

    def has_permission(self, request, view):
        is_authenticated = super(TOTPAuthenticated, self).has_permission(request=request, view=view)

        def test(user):
            return user.is_verified() or (user.is_authenticated and not user_has_device(user))

        return test(request.user) and is_authenticated


class BlacklistPermission(permissions.BasePermission):
    """
    Global permission check for whitelisted IPs.
    """

    def has_permission(self, request, view):
        ip_addr = request.META['REMOTE_ADDR']

        if ip_addr in settings.ALLOWED_HOSTS:
            message = f"this IP Address: {str(ip_addr)} is from the IPs white list"
            DATA_LOGGER.debug(f"[message] [DISBURSEMENT ACTION ABILITY] [{request.user}] -- {message}")
            return True

        message = f"this IP Address: {str(ip_addr)} is not from the IPs white list"
        DATA_LOGGER.debug(f"[message] [DISBURSEMENT ACTION ABILITY] [{request.user}] -- {message}")
        return False
