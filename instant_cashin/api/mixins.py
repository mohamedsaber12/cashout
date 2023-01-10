# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework.permissions import BasePermission
from rest_framework.settings import api_settings


class APIViewPaginatorMixin:
    """
    Paginator mixin for the APIView classes
    """

    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS

    @property
    def paginator(self):
        """
        The paginator instance associated with the view, or `None`.
        """
        if not hasattr(self, '_paginator'):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def paginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        """
        Return a paginated style `Response` object for the given output data.
        """
        assert self.paginator is not None
        return self.paginator.get_paginated_response(data)


class IsInstantAPICheckerUser(BasePermission):
    """
    Verify that the current user is an instant api checker user
    """

    def has_permission(self, request, view):
        return request.user.is_instantapichecker


class IsSystemAdminUser(BasePermission):
    """
    Verify that the current user is an system admin user
    """

    def has_permission(self, request, view):
        return request.user.is_system_admin
