# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import password_validation
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy

from .forms import CheckerCreationAdminForm, MakerCreationAdminForm, RootCreationForm, UserChangeForm
from .models import (CheckerUser, Client, EntitySetup, InstantAPICheckerUser,
                     InstantAPIViewerUser, MakerUser, RootUser, Setup, SupportUser, SupportSetup,
                     SuperAdminUser, User)

from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from data.tasks import ExportClientsTransactionsMonthlyReportTask
from disbursement.views import ExportClientsTransactionsMonthlyReport

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
            user_deactivated_log_msg = f"[message] [User Deactivated] [{request.user}] -- {obj.username}"
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
            user_activated_log_msg = f"[message] [User Activated] [{request.user}] -- activated user: {obj.username}"
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
        if request.user.is_superuser or request.user.is_finance \
                or request.user.is_finance_with_instant_transaction_view:
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
            MODIFIED_USERS_LOGGER.debug(
                    f"[message] [{self.logged_user_type.capitalize()} User Modified] [{request.user}] "
                    f"-- Modified user with username: {obj.username}"
            )

        else:
            CREATED_USERS_LOGGER.debug(
                    f"[message] [{self.logged_user_type} User Created] [{request.user}] "
                    f"-- Created new {self.logged_user_type.lower()} with username: {obj.username}"
            )
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
            MODIFIED_USERS_LOGGER.debug(
                    f"[message] [Admin User Modified] [{request.user}] -- Modified user: {obj.username}"
            )
        else:
            CREATED_USERS_LOGGER.debug(
                    f"[message] [Admin User Created] [{request.user}] -- Created new root/admin: {obj.username}"
            )
        super(RootAdmin, self).save_model(request, obj, form, change)


@admin.register(SuperAdminUser)
class SuperAdmin(UserAccountAdmin):
    
    actions = ['activate_selected', 'deactivate_selected', "export_report"]
    extended_actions = ['activate_selected', 'deactivate_selected', "export_report"]
    
    def get_actions(self, request):
        actions = super(UserAccountAdmin, self).get_actions(request)
        if request.user.is_finance:
            if 'activate_selected' in actions:
                del actions['activate_selected']
            if 'deactivate_selected' in actions:
                del actions['deactivate_selected']
        return actions
    
    # def get_extended_actions(self, request):
    #     ext_actions = super(UserAccountAdmin, self).get_extended_actions(request)
    #     if request.user.is_finance:
    #         del ext_actions['activate_selected', 'deactivate_selected']
    #     return ext_actions
    
    def has_module_permission(self, request):
        if request.user.is_superuser or request.user.is_finance \
                or request.user.is_finance_with_instant_transaction_view:
            return True
        
    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser or request.user.is_finance \
                or request.user.is_finance_with_instant_transaction_view:
            return True
    
    def get_fieldsets(self, request, obj=None):
        fieldsets = super(SuperAdmin, self).get_fieldsets(request, obj)
        # pop parent field from fieldsets
        fieldsets[2][1]['fields'] = ('is_active', 'is_staff', 'is_superuser')
        self.fieldsets = fieldsets
        return self.fieldsets

    def save_model(self, request, obj, form, change):
        if obj.pk is not None:
            MODIFIED_USERS_LOGGER.debug(
                    f"[message] [SuperAdmin User Modified] [{request.user}] -- Modified user: {obj.username}"
            )

        else:
            CREATED_USERS_LOGGER.debug(
                    f"[message] [SuperAdmin User Created] [{request.user}] -- Created new super-user: {obj.username}"
            )
        super(SuperAdmin, self).save_model(request, obj, form, change)
        
    def export_report(self, request, queryset):
        """export report for selected list of users"""
        
        if 'apply' in request.POST:
            # queryset.update(env='hard coded response')
            start_date = request.POST.get("start_date")
            end_date = request.POST.get("end_date")
            status = request.POST.get("status")
            ExportClientsTransactionsMonthlyReportTask.delay(
                request.user.id, start_date, end_date, status,
                list(queryset.values_list('pk', flat=True))
            )
            # exportObject = ExportClientsTransactionsMonthlyReport()
            # report_download_url = exportObject.run(request.user.id, start_date, end_date, status, list(queryset.values_list('pk', flat=True)))

            self.message_user(request, f"The report will send  to your email in a few minutes")
            return HttpResponseRedirect(request.get_full_path())
        
        return render(request,
                      'admin/all_superadmins_report.html',
                      context={'superadmins': queryset})

    export_report.short_description = ugettext_lazy("export report selected %(verbose_name_plural)s")



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
class SupportUserModelAdmin(UserAccountAdmin):
    """
    Manages support user model at the admin panel
    """

    list_display = ['username', 'first_name', 'last_name', 'email', 'mobile_no']
    
    def get_fieldsets(self, request, obj):
        return ((None, {'classes': ('wide',), 'fields': ('username', 'password1', 'password2')}), ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'mobile_no')}), ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}), ('Important dates', {'fields': ('last_login', 'date_joined')}))
    
    def get_fields(self):
        return ((None, {'classes': ('wide',), 'fields': ('username', 'password1', 'password2')}), ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'mobile_no')}), ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}), ('Important dates', {'fields': ('last_login', 'date_joined')}))


@admin.register(SupportSetup)
class SupportSetupModelAdmin(admin.ModelAdmin):
    """
    Manages support user setup model at the admin panel
    """

    list_display = ['user_created', 'support_user', 'can_onboard_entities']
    list_filter = ['user_created']
    
@admin.register(User)
class UserAdmin(UserAdmin):

    form = UserChangeForm

    list_display = ('email', )
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Important dates', {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')}
        ),
    )


# ToDo: Custom general user model
# admin.site.register(User)
admin.site.register(Client)

