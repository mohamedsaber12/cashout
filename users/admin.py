# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django import forms
from django.contrib import admin
from django.contrib.auth import password_validation
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy

from data.utils import get_client_ip

from .forms import CheckerCreationAdminForm, MakerCreationAdminForm, RootCreationForm, UserChangeForm
from .models import (CheckerUser, Client, EntitySetup, InstantAPICheckerUser,
                     InstantAPIViewerUser, MakerUser, RootUser, Setup, SupportUser, SupportSetup,
                     SuperAdminUser, User)

CREATED_USERS_LOGGER = logging.getLogger("created_users")
MODIFIED_USERS_LOGGER = logging.getLogger("modified_users")
DELETED_USERS_LOGGER = logging.getLogger("delete_users")
# TODO: I need to check querysets for all for children
# TODO: Add logs for deleting and adding any instance


class UserAccountAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'is_active')
    filter_horizontal = ('groups',)
    actions = ['activate_selected', 'deactivate_selected']
    extended_actions = ['activate_selected', 'deactivate_selected']

    def deactivate_selected(self, request, queryset):
        """Deactivate selected list of users"""

        if not self.has_change_permission(request):
            raise PermissionDenied

        for obj in queryset:
            user_deactivated_log_msg = "[User Deactivated]" + \
                    f"\nUser: {request.user} from IP Address: {get_client_ip(request)} deactivated user: {obj.username}"
            if not obj.is_active:
                continue
            else:
                MODIFIED_USERS_LOGGER.debug(user_deactivated_log_msg)

            obj.is_active = False
            obj.save()

    deactivate_selected.short_description = ugettext_lazy("Deactivate selected %(verbose_name_plural)s")

    def activate_selected(self, request, queryset):
        """Activate selected list of users"""

        if not self.has_change_permission(request):
            raise PermissionDenied

        for obj in queryset:
            user_activated_log_msg = "[User Activated]" + \
                      f"\nUser: {request.user} from IP Address: {get_client_ip(request)} activated user: {obj.username}"
            if obj.is_active:
                continue
            else:
                MODIFIED_USERS_LOGGER.debug(user_activated_log_msg)

            obj.is_active = True
            obj.save()

    activate_selected.short_description = ugettext_lazy("Activate selected %(verbose_name_plural)s")

    def get_list_display(self, request):
        list_display = super(UserAccountAdmin, self).get_list_display(request)
        if request.user.is_superuser:
            list_display = ('username', 'first_name', 'last_name', 'email', 'groups', 'is_active', 'user_type')
            return list_display
        return list_display

    def get_form(self, request, obj=None, **kwargs):
        userform = super(UserAccountAdmin, self).get_form(request, obj=obj, **kwargs)
        userform.request = request
        userform.request.obj = obj
        defaults = {}
        if obj:
            defaults['form'] = UserChangeForm
        else:
            defaults['form'] = userform
        defaults.update(kwargs)
        return super(UserAccountAdmin, self).get_form(request, obj, **defaults)

    def get_fieldsets(self, request, obj=None):
        perm_fields = ('is_active', 'is_staff')
        if not obj:
            if request.user.is_superuser:
                perm_fields = ('is_active', 'is_staff', 'is_superuser', 'parent')

            self.add_fieldsets = (
                (None, {
                    'classes': ('wide',),
                    'fields': ('username', 'password1', 'password2',)}
                 ),
                (_('Personal info'), {
                 'fields': ('first_name', 'last_name', 'email', 'mobile_no')}),
                (_('Permissions'), {'fields': perm_fields}),
                (_('Important dates'), {
                 'fields': ('last_login', 'date_joined')})
            )

        elif obj:
            perm_fields = ('is_active', 'is_staff', 'user_type')
            self.add_fieldsets = (
                (None, {
                    'classes': ('wide',),
                    'fields': ('username', 'email', 'password')}
                 ),
                (_('Personal info'), {
                 'fields': ('first_name', 'last_name', 'mobile_no')}),
                (_('Permissions'), {'fields': perm_fields}),
                (_('Important dates'), {
                 'fields': ('last_login', 'date_joined')})
            )

        return self.add_fieldsets

    def get_queryset(self, request):
        qs = super(UserAccountAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        elif request.user.is_root:
            qs = qs.filter(hierarchy=request.user.hierarchy)
            return qs
        else:
            return request.user.brothers()


class BaseChildAdmin(UserAccountAdmin):
    """
    Base Child Admin Class to be inherited by all of children
    """
    logged_user_type = 'Child'

    def save_model(self, request, obj, form, change):
        # TODO : FIX Parent hierarchy
        if request.user.is_superuser:
            obj.hierarchy = form.cleaned_data['parent'].hierarchy
        else:
            obj.hierarchy = request.user.hierarchy

        if obj.pk is not None:
            MODIFIED_USERS_LOGGER.debug(f"""[{self.logged_user_type.capitalize()} User Modified]
            User: {request.user.username}
            Modified user with username: {obj.username} from IP Address {get_client_ip(request)}""")

        else:
            CREATED_USERS_LOGGER.debug(f"""[{self.logged_user_type} User Created]
            User: {request.user.username}
            Created new {self.logged_user_type.lower()} with username: {obj.username}""")
        obj.save()


@admin.register(MakerUser)
class MakerAdmin(BaseChildAdmin):
    """
    Manages makers from the admin panel
    """
    add_form = MakerCreationAdminForm
    logged_user_type = 'Maker'


@admin.register(CheckerUser)
class CheckerAdmin(BaseChildAdmin):
    """
    Manages checkers from the admin panel
    """
    add_form = CheckerCreationAdminForm
    logged_user_type = 'Checker'


@admin.register(InstantAPICheckerUser)
class InstantAPICheckerAdmin(BaseChildAdmin):
    """
    Manages instant api checkers from the admin panel
    """
    add_form = MakerCreationAdminForm
    logged_user_type = 'Instant API Checker'


@admin.register(InstantAPIViewerUser)
class InstantAPIViewerAdmin(BaseChildAdmin):
    """
    Manages instant api viewers from the admin panel
    """
    add_form = MakerCreationAdminForm
    logged_user_type = 'Instant API Viewer'


class RootCreationAdminForm(RootCreationForm):

    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput,
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput,
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )


@admin.register(RootUser)
class RootAdmin(UserAccountAdmin):
    add_form = RootCreationAdminForm

    def get_fieldsets(self, request, obj=None):
        fieldsets = super(RootAdmin, self).get_fieldsets(request, obj)
        # pop parent field from fieldsets
        fieldsets[2][1]['fields'] = ('is_active', 'is_staff', 'is_superuser')
        self.fieldsets = fieldsets
        return self.fieldsets

    def save_model(self, request, obj, form, change):
        if obj.pk is not None:
            MODIFIED_USERS_LOGGER.debug(f"""[Admin User Modified]
            User: {request.user.username}
            Modified user with username: {obj.username} from IP Address {get_client_ip(request)}""")
        else:
            CREATED_USERS_LOGGER.debug(f"""[Admin User Created]
            User: {request.user.username}
            Created new root/admin with username: {obj.username}""")
        super(RootAdmin, self).save_model(request, obj, form, change)


@admin.register(SuperAdminUser)
class SuperAdmin(UserAccountAdmin):
    def get_fieldsets(self, request, obj=None):
        fieldsets = super(SuperAdmin, self).get_fieldsets(request, obj)
        # pop parent field from fieldsets
        fieldsets[2][1]['fields'] = ('is_active', 'is_staff', 'is_superuser')
        self.fieldsets = fieldsets
        return self.fieldsets

    def save_model(self, request, obj, form, change):
        if obj.pk is not None:
            MODIFIED_USERS_LOGGER.debug(f"""[SuperAdmin User Modified]
            User: {request.user.username}
            Modified user with username: {obj.username} from IP Address {get_client_ip(request)}""")

        else:
            CREATED_USERS_LOGGER.debug(f"""[SuperAdmin User Created]
            User: {request.user.username}
            Created new super-user with username: {obj.username}""")
        super(SuperAdmin, self).save_model(request, obj, form, change)


@admin.register(Setup)
class SetupRootAdmin(admin.ModelAdmin):
    """
    Custom the setup model to check on-boarding step easily
    """

    list_display = [
        'user', 'pin_setup', 'levels_setup', 'maker_setup', 'checker_setup', 'category_setup', 'collection_setup'
    ]
    readonly_fields = ['user']


@admin.register(EntitySetup)
class EntitySetupAdmin(admin.ModelAdmin):
    """
    Customize entity_setup view at the admin panel
    """

    list_display = ['entity', 'user', 'is_normal_flow', 'agents_setup', 'fees_setup']
    list_filter = ['user']


@admin.register(SupportUser)
class SupportUserModelAdmin(admin.ModelAdmin):
    """
    Manages support user model at the admin panel
    """

    list_display = ['username', 'first_name', 'last_name', 'email', 'mobile_no']


@admin.register(SupportSetup)
class SupportSetupModelAdmin(admin.ModelAdmin):
    """
    Manages support user setup model at the admin panel
    """

    list_display = ['user_created', 'support_user', 'can_onboard_entities']


# ToDo: Custom general user model
admin.site.register(User)
admin.site.register(Client)
