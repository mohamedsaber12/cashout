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


class SuperOrRootRequiredMixin(LoginRequiredMixin):
    """
    Give the access permission of a certain view to only Super or Root users
    """
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superadmin or request.user.is_root):
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