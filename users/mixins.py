# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .models import SupportSetup, Client, User


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


class SupportUserRequiredMixin(LoginRequiredMixin):
    """
    Mixin to give access permission for only support users
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_support:
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


class ProfileOwnerOrMemberRequiredMixin(UserPassesTestMixin, LoginRequiredMixin):
    """
    Give the access permission of a profile detail/edit view to only current user or member of the current user
    """

    def test_func(self):
        profile_username = self.request.resolver_match.kwargs.get('username')
        current_user = self.request.user

        if profile_username:
            if profile_username == current_user.username:
                return True
            elif current_user.is_superadmin:
                client_setups = Client.objects.filter(creator=current_user).select_related('client')
                support_setups = SupportSetup.objects.filter(user_created=current_user).select_related('support_user')
                members_list = [obj.client.username for obj in client_setups]
                members_list += [obj.support_user.username for obj in support_setups]
                if profile_username in members_list:
                    return True
            elif current_user.is_root:
                members_objects = User.objects.get_all_hierarchy_tree(current_user.hierarchy)
                members_list = [user.username for user in members_objects]
                if profile_username in members_list:
                    return True

        return False
