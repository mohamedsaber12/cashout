# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import csv

from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from core.models import AbstractBaseStatus
from .models.instant_transactions import AbstractBaseIssuer

class IntegrationUserAndSupportUserPassesTestMixin(UserPassesTestMixin, LoginRequiredMixin):
    """
    Mixin for giving access to integration patch related views.

    Cases:
        > Admin/Support/Instant viewer user with integration patch onboarding permissions
    """

    def test_func(self):
        if self.request.user.is_instant_model_onboarding and \
                (self.request.user.is_root or self.request.user.is_instantapiviewer or self.request.user.is_support):
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


class RootWithInstantPermissionsPassesTestMixin(UserPassesTestMixin, LoginRequiredMixin):
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


class ExportCsvMixin:
    """
    mixin class to add  export to any model
    """
    def export_as_csv(self, request, queryset):

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            obj.status = [st for st in AbstractBaseStatus.STATUS_CHOICES
                          if st[0] == obj.status][0][1]
            obj.issuer_type = [iss for iss in AbstractBaseIssuer.ISSUER_TYPE_CHOICES
                          if iss[0] == obj.issuer_type][0][1]
            row = writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export Selected"