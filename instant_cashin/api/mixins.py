from rest_framework.permissions import BasePermission


class IsInstantAPICheckerUser(BasePermission):
    """Verify that the current user is an instant api checker user"""
    def has_permission(self, request, view):
        return request.user.is_instantapichecker
