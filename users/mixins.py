# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .models import SupportSetup, Client, User, SuperAdminUser, OnboardUserSetup, SupervisorSetup


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


class MakeTransferRequestPermissionRequired(UserPassesTestMixin, LoginRequiredMixin):
    """
    Admin user with any onboarding business model but the standard vodafone one.
    """

    def test_func(self):
        if not (self.request.user.is_vodafone_default_onboarding or self.request.user.is_banks_standard_model_onboaring) and (
                self.request.user.is_root or self.request.user.is_instantapiviewer
        ):
            return True

        return False


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

class SuperOrOnboardUserRequiredMixin(LoginRequiredMixin):

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superadmin or request.user.is_onboard_user):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class SuperAdminOrSupervisorUserRequiredMixin(LoginRequiredMixin):

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_superadmin or request.user.is_supervisor):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class UserWithDefaultOnboardingPermissionRequired(UserPassesTestMixin, LoginRequiredMixin):
    """
    Check if the user has the default vodafone onboarding permission
    """

    def test_func(self):
        if self.request.user.is_vodafone_default_onboarding or self.request.user.is_banks_standard_model_onboaring:
            return True

        return False


class UserWithInstantOnboardingPermissionRequired(UserPassesTestMixin, LoginRequiredMixin):
    """
    Check if the user has the instant model onboarding permission
    """

    def test_func(self):
        if self.request.user.is_instant_model_onboarding:
            return True

        return False


class AgentsListPermissionRequired(UserPassesTestMixin, LoginRequiredMixin):
    """
    Check if the user has the right to access the agents list view.

    Cases:
        1. Superadmin user with any on boarding setups other than the standard vodafone model.
        2. Support user with on boarding setups of the standard vodafone model.
    """

    def test_func(self):
        if self.request.user.is_superadmin and not self.request.user.is_vodafone_default_onboarding:
            return True
        elif self.request.user.is_support and self.request.user.is_vodafone_default_onboarding:
            return True
        elif self.request.user.is_support and self.request.user.is_banks_standard_model_onboaring:
            return True

        return False


class SuperWithAcceptVFAndVFFacilitatorOnboardingPermissionRequired(LoginRequiredMixin):
    """
    Mixin to give access permission for only support users
    """

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_accept_vodafone_onboarding or request.user.is_vodafone_facilitator_onboarding):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class UserWithAcceptVFOnboardingPermissionRequired(UserPassesTestMixin, LoginRequiredMixin):
    """
    Check if the user has the accept vodafone onboarding permission
    """

    def test_func(self):
        if self.request.user.is_accept_vodafone_onboarding:
            return True

        return False


class UserWithDisbursementPermissionRequired(UserPassesTestMixin, LoginRequiredMixin):
    """
    Check if the user has disbursement permission and from a disbursement family
    """

    def test_func(self):
        status = self.request.user.get_status(self.request)

        if status == "disbursement" and \
                (self.request.user.is_maker or self.request.user.is_checker or self.request.user.is_root):
            return True

        return False


# class UserWithAbnormalFlowDisbursementPermissionRequired(UserPassesTestMixin, LoginRequiredMixin):
#     """
#     Check if the user has disbursement permission and from a disbursement family
#     """
#
#     def test_func(self):
#         status = self.request.user.get_status(self.request)
#
#         if status == "disbursement" and \
#                 (self.request.user.is_root and not self.request.user.root_entity_setups.is_normal_flow) or \
#                 (
#                         self.request.user.is_maker or self.request.user.is_checker and
#                         not self.request.user.root.root_entity_setups.is_normal_flow
#                 ):
#             return True
#
#         return False


class SupportUserRequiredMixin(LoginRequiredMixin):
    """
    Mixin to give access permission for only support users
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_support:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class OnboardUserRequiredMixin(LoginRequiredMixin):
    """
    Mixin to give access permission for only onboard users
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_onboard_user:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class SupervisorUserRequiredMixin(LoginRequiredMixin):
    """
    Mixin to give access permission for only supervisor users
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_supervisor:
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
        elif self.request.user.is_onboard_user:
            entity_admin_username = self.request.resolver_match.kwargs.get('username')

            for client_obj in self.request.user.my_onboard_setups.user_created.clients.all():
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

        return self.request.user.is_root or self.request.user.is_instantapiviewer


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
        if request.user.is_superadmin and not request.user.has_uncomplete_entity_creation():
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
                onboard_user_setups = OnboardUserSetup.objects.filter(user_created=current_user). \
                    select_related('onboard_user')
                supervisor_setups = SupervisorSetup.objects.filter(user_created=current_user). \
                    select_related('supervisor_user')
                members_list = [obj.client.username for obj in client_setups]
                members_list += [obj.support_user.username for obj in support_setups]
                members_list += [obj.onboard_user.username for obj in onboard_user_setups]
                members_list += [obj.supervisor_user.username for obj in supervisor_setups]
                if profile_username in members_list:
                    return True
            elif current_user.is_root:
                members_objects = User.objects.get_all_hierarchy_tree(current_user.hierarchy)
                members_list = [user.username for user in members_objects]
                if profile_username in members_list:
                    return True
            elif current_user.is_supervisor:
                support_setups = SupportSetup.objects.filter(supervisor=current_user).select_related('support_user')
                members_list = [obj.support_user.username for obj in support_setups]
                if profile_username in members_list:
                    return True
            elif current_user.is_onboard_user:
                client_setups = Client.objects.filter(onboarded_by=current_user).select_related('client')
                members_list = [obj.client.username for obj in client_setups]
                if profile_username in members_list:
                    return True

        return False


class UserOwnsMemberRequiredMixin(UserPassesTestMixin, LoginRequiredMixin):
    """
    Give the access permission of a user to only the admin/creator of it.
    """

    def test_func(self):
        target_is_client_member = self.request.POST.get('client', False)
        target_is_support_member = self.request.POST.get('support', False)
        target_is_entity_member = self.request.POST.get('entity', False)
        target_id = int(self.request.POST.get('user_id', False))
        current_user = self.request.user

        if target_id:
            if current_user.is_superadmin and (target_is_client_member or target_is_support_member):
                client_setups = Client.objects.filter(creator=current_user).select_related('client')
                support_setups = SupportSetup.objects.filter(user_created=current_user).select_related('support_user')
                members_ids_list = [obj.id for obj in client_setups] + [obj.id for obj in support_setups]
                if target_id in members_ids_list:
                    return True
            elif current_user.is_root and target_is_entity_member:
                members_objects = User.objects.get_all_hierarchy_tree(current_user.hierarchy)
                members_ids_list = [user.id for user in members_objects]
                if target_id in members_ids_list:
                    return True
            elif current_user.is_supervisor and target_is_support_member:
                support_setup = SupportSetup.objects.get(id=int(target_id))
                if support_setup.supervisor == current_user:
                    return True

        return False


class SupportOrRootOrMakerUserPassesTestMixin(UserPassesTestMixin, LoginRequiredMixin):
    """
    Give the access permission to the support user to specific admin if this admin is member of the support creator.
    Or if the user is root or maker give him/her access immediately.
    """

    def test_func(self):
        admin = self.request.GET.get('admin', False)
        username = self.request.resolver_match.kwargs.get('username')
        admin_username = admin if admin else username

        if self.request.user.is_root or self.request.user.is_maker or self.request.user.is_uploader or \
                self.request.user.is_upmaker:
            return True
        elif self.request.user.is_support and admin_username:
            support_creator = self.request.user.my_setups.user_created
            all_super_admins = [support_creator]

            # get all super admins that has same permission
            if support_creator.is_vodafone_default_onboarding:
                all_super_admins = [x for x in SuperAdminUser.objects.all() if x.is_vodafone_default_onboarding]
            elif support_creator.is_instant_model_onboarding:
                all_super_admins = [x for x in SuperAdminUser.objects.all() if x.is_instant_model_onboarding]
            elif support_creator.is_accept_vodafone_onboarding:
                all_super_admins = [x for x in SuperAdminUser.objects.all() if x.is_accept_vodafone_onboarding]
            elif support_creator.is_vodafone_facilitator_onboarding:
                all_super_admins = [x for x in SuperAdminUser.objects.all() if x.is_vodafone_facilitator_onboarding]
            elif support_creator.is_banks_standard_model_onboaring:
                all_super_admins = [x for x in SuperAdminUser.objects.all() if x.is_banks_standard_model_onboaring]

            client_setups = Client.objects.filter(creator__in=all_super_admins).select_related('client')
            members_list = [obj.client.username for obj in client_setups]
            if admin_username in members_list:
                return True

        return False
