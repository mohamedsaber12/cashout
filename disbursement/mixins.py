# -*- coding: UTF-8 -*-
from __future__ import unicode_literals


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
