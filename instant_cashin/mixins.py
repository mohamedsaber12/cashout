# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class InstantReviewerRequiredMixin(LoginRequiredMixin):
    """
    Prevent non logged-in or non instant-viewer users from accessing instant transactions.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_instantapiviewer:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class RootFromInstantFamilyRequiredMixin(UserPassesTestMixin, LoginRequiredMixin):
    """
    Prevent non logged-in and admins who not belong to instant family accessing instant cashin home view.
    """

    def test_func(self):
        if (
                self.request.user.is_root and
                any([True for us in self.request.user.children() if us.is_instantapichecker or us.is_instantapiviewer])
        ):
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
