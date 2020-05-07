# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class ParentPermissionMixin(object):
    def has_add_permission(self, request):
        if request.user.is_root or request.user.is_superuser or request.user.has_perm('auth.add_group'):
            super(ParentPermissionMixin, self).has_add_permission(request)
            return True

    def has_change_permission(self, request, obj=None):
        if request.user.is_root or request.user.is_superuser or request.user.has_perm('auth.change_group'):
            super(ParentPermissionMixin, self).has_change_permission(request, obj)
            return True

    def has_delete_permission(self, request, obj=None):
        if request.user.is_root or request.user.is_superuser or request.user.has_perm('auth.delete_group'):
            super(ParentPermissionMixin, self).has_delete_permission(request, obj)
            return True


class RootRequiredMixin(LoginRequiredMixin):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_root:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class CollectionRootRequiredMixin(RootRequiredMixin):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.get_status(request) == 'collection':
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class DisbursementRootRequiredMixin(RootRequiredMixin):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.get_status(request) == 'disbursement':
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class SuperRequiredMixin(LoginRequiredMixin):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superadmin:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class SuperOwnsClientRequiredMixin(UserPassesTestMixin, LoginRequiredMixin):
    """
    Give the access permission of a certain view to only SuperAdmin users,
    Considering: SuperAdmin MUST owns that entity we're trying to manage.
    """

    def test_func(self):
        """Test if the current SuperAdmin owns the entity we're trying to manage"""
        if self.request.user.is_superadmin:
            entity_admin_username = self.request.resolver_match.kwargs.get('username')

            for client_obj in self.request.user.clients.all():
                if client_obj.client.username == entity_admin_username:
                    return True

        return False


class SuperOrRootOwnsCustomizedBudgetClientRequiredMixin(UserPassesTestMixin, LoginRequiredMixin):
    """
    Give the access permission of a certain view to only Super or Root users,
    Considering:
        - If the user is a SuperAdmin:
            1) SuperAdmin MUST owns the entity being balance inquired at.
            2) And entity being balance inquired at MUST has custom budget.
    """

    def test_func(self):
        if self.request.user.is_superadmin:
            entity_admin_username = self.request.resolver_match.kwargs.get('username')

            for client_obj in self.request.user.clients.all():
                if client_obj.client.username == entity_admin_username:
                    if client_obj.client.has_custom_budget:
                        return True

        return self.request.user.is_root


class SuperOwnsCustomizedBudgetClientRequiredMixin(UserPassesTestMixin, LoginRequiredMixin):
    """
    Give the access permission of a certain view to only SuperAdmin users,
    Considering:
        - If the user is a SuperAdmin:
            1) SuperAdmin MUST owns the entity that we're trying to manage its custom budget.
            2) And that entity MUST has custom budget.
    """

    def test_func(self):
        if self.request.user.is_superadmin:
            entity_admin_username = self.request.resolver_match.kwargs.get('username')

            for client_obj in self.request.user.clients.all():
                if client_obj.client.username == entity_admin_username:
                    if client_obj.client.has_custom_budget:
                        return True

        return False


class SuperFinishedSetupMixin(LoginRequiredMixin):
    """
    Prevent superuser from accessing entity setup views if he already finished it.
    Must be used after SuperRequiredMixin.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_uncomplete_entity_creation():
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
