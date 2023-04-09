# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class IntegrationUserAndSupportUserPassesTestMixin(
    UserPassesTestMixin, LoginRequiredMixin
):
    """
    Mixin for giving access to integration patch related views.

    Cases:
        > Admin/Support/Instant viewer user with integration patch onboarding permissions
    """

    def test_func(self):
        if self.request.user.is_instant_model_onboarding and (
            self.request.user.is_root
            or self.request.user.is_instantapiviewer
            or self.request.user.is_support
        ):
            return True

        return False


class InstantReviewerRequiredMixin(LoginRequiredMixin):
    """
    Prevent non logged-in or non instant-viewer users from accessing instant transactions.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_instantapiviewer:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class RootWithInstantPermissionsPassesTestMixin(
    UserPassesTestMixin, LoginRequiredMixin
):
    """
    Prevent non logged-in and admins who not belong to instant family accessing instant cashin home view.
    """

    def test_func(self):
        if self.request.user.is_root and self.request.user.is_instant_model_onboarding:
            return True

        return False


class RootOwnsRequestedFileTestMixin(UserPassesTestMixin):
    """
    Check if the request to-serve-download file is owned by current Admin
    """

    def test_func(self):
        """Test if the Admin username is the same as the file owner string"""
        filename = self.request.GET.get('filename', None)
        return filename and filename.split('_')[1] == self.request.user.username
