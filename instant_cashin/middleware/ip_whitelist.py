import logging

from django.core.exceptions import PermissionDenied

IP_LOGGER = logging.getLogger("access")


class FilterIPMiddleware(object):
    def __init__(self, get_response):
        """
        One-time configuration and initialisation.
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        Code to be executed for each request before the view (and later
        middleware) are called.
        """
        response = self.get_response(request)
        return response

    # Check if client IP address is allowed
    def process_view(self, request, view_func, view_args, view_kwargs):

        whitelisted_ip = [
            "34.251.217.198",
            "172.31.8.189",
            "172.31.23.159",
            "75.2.116.217",
            "99.83.194.66",
            "172.31.29.238",
            "52.31.227.79",
        ]
        if request.user.is_authenticated and request.user.is_instantapichecker:
            ip = request.META.get("REMOTE_ADDR")
            IP_LOGGER.debug(
                f"[message] [IP] [{request.user.username}] -- request Ip [REMOTE_ADDR] :-  {ip}"
            )
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            IP_LOGGER.debug(
                f"[message] [IP] [{request.user.username}] -- request Ip [X FORWARDED] :-  {x_forwarded_for}"
            )
            IP_LOGGER.debug(
                f"[message] [IP] [{request.user.username}] -- request data :-  {request}"
            )
            # if 'eksab' in request.user.root.username and ip not in whitelisted_ip:
            # raise PermissionDenied()

        return None
