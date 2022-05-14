# -*- coding: UTF-8 -*-
from __future__ import unicode_literals
import csv

from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext as _

from utilities.models.abstract_models import AbstractBaseACHTransactionStatus
from disbursement.models import BankTransaction


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
            if queryset.model is BankTransaction:
                obj.status = [st for st in AbstractBaseACHTransactionStatus.STATUS_CHOICES
                              if st[0] == obj.status][0][1]
            row = writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Export Selected"
