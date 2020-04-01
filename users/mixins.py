from django.contrib.auth.mixins import LoginRequiredMixin


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
        if not (request.user.is_authenticated and request.user.is_root):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class CollectionRootRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_root and request.user.get_status(request) == 'collection'):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class DisbursementRootRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_root and request.user.get_status(request) == 'disbursement'):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class SuperRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_superadmin):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class SuperOwnsClientRequiredMixin(LoginRequiredMixin):
    """
    Give the access permission of a certain view to only SuperAdmin users,
    Considering: SuperAdmin MUST owns that entity we're trying to manage.
    """
    def dispatch(self, request, *args, **kwargs):
        has_permission = False

        if request.user.is_superadmin and request.user.is_authenticated:
            entity_admin_username = request.resolver_match.kwargs.get('username')

            for client_obj in request.user.clients.all():
                if client_obj.client.username == entity_admin_username:
                    has_permission = True

        if not has_permission:
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)


class SuperOrRootOwnsCustomizedBudgetClientRequiredMixin(LoginRequiredMixin):
    """
    Give the access permission of a certain view to only Super or Root users,
    Considering:
        - If the user is a SuperAdmin:
            1) SuperAdmin MUST owns the entity being balance inquired at.
            2) And entity being balance inquired at MUST has custom budget.
    """
    def dispatch(self, request, *args, **kwargs):
        has_permission = False

        if request.user.is_superadmin:
            entity_admin_username = request.resolver_match.kwargs.get('username')

            for client_obj in request.user.clients.all():
                if client_obj.client.username == entity_admin_username:
                    if client_obj.client.has_custom_budget:
                        has_permission = True

        if request.user.is_root:
            has_permission = True

        if not has_permission:
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)


class SuperOwnsCustomizedBudgetClientRequiredMixin(LoginRequiredMixin):
    """
    Give the access permission of a certain view to only SuperAdmin users,
    Considering:
        - If the user is a SuperAdmin:
            1) SuperAdmin MUST owns the entity that we're trying to manage its custom budget.
            2) And that entity MUST has custom budget.
    """
    def dispatch(self, request, *args, **kwargs):
        has_permission = False

        if request.user.is_superadmin:
            entity_admin_username = request.resolver_match.kwargs.get('username')

            for client_obj in request.user.clients.all():
                if client_obj.client.username == entity_admin_username:
                    if client_obj.client.has_custom_budget:
                        has_permission = True

        if not has_permission:
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)


class SuperFinishedSetupMixin(LoginRequiredMixin):
    """
    Prevent superuser from accessing entity setup views if he already finished it.
    Must be used after SuperRequiredMixin.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_uncomplete_entity_creation():
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class InstantReviewerRequiredMixin(LoginRequiredMixin):
    """
    Prevent non logged-in or non instant-viewer users from accessing instant transactions.
    """
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_authenticated and request.user.is_instantapiviewer):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)