# -*- coding: UTF-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext as _


class AdminSiteOwnerOnlyPermissionMixin:
    """
    For handling add/change/delete permission at the admin panel
    """

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser or request.user == obj.doc.owner.root.super_admin or \
                request.user == obj.doc.owner.root:
            return True
        raise PermissionError(_("Only admin family member users allowed to delete records from this table."))

    def has_change_permission(self, request, obj=None):
        return False


class AdminOrCheckerRequiredMixin(LoginRequiredMixin):
    """
    Check if the user accessing resource is admin or checker with disbursement and accept vf on-boarding permissions
    """

    def dispatch(self, request, *args, **kwargs):
        status = self.request.user.get_status(self.request)

        if not (status == "disbursement" and
                self.request.user.is_accept_vodafone_onboarding and
                (self.request.user.is_checker or self.request.user.is_root)):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class AdminOrCheckerOrSupportRequiredMixin(LoginRequiredMixin):
    """
    Check if the user accessing resource is admin or checker or support
    with disbursement and accept vf on-boarding permissions
    """

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_support and self.request.user.is_accept_vodafone_onboarding:
            return super().dispatch(request, *args, **kwargs)
        else:
            status = self.request.user.get_status(self.request)

            if not (status == "disbursement" and
                    self.request.user.is_accept_vodafone_onboarding and
                    (self.request.user.is_checker or self.request.user.is_root)):
                return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
