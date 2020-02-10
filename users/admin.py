import logging

from django import forms
from django.contrib import admin
from django.contrib.admin.actions import delete_selected as delete_selected_
from django.contrib.auth import password_validation
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy

from data.utils import get_client_ip

from .forms import CheckerCreationAdminForm, MakerCreationAdminForm, RootCreationForm, UserChangeForm
from .models import CheckerUser, Client, InstantAPICheckerUser, MakerUser, RootUser, SuperAdminUser, User


CREATED_USERS_LOGGER = logging.getLogger("created_users")
MODIFIED_USERS_LOGGER = logging.getLogger("modified_users")
DELETED_USERS_LOGGER = logging.getLogger("delete_users")
DELETED_GROUPS_LOGGER = logging.getLogger("delete_groups")
admin.site.unregister(Group)


# TODO: I need to check querysets for all for children
# TODO: Add logs for deleting and adding any instance

def delete_selected(modeladmin, request, queryset):
    if not modeladmin.has_delete_permission(request):
        raise PermissionDenied
    if request.POST.get('post'):
        for obj in queryset:
            user_deleted_log_msg = f"""[User Deleted]
            User: {request.user.username}
            Deleted user with username: {obj.username} from IP Address {get_client_ip(request)}"""
            if 'MyUser' in modeladmin.__str__():
                DELETED_USERS_LOGGER.debug(user_deleted_log_msg)
            else:
                DELETED_GROUPS_LOGGER.debug(user_deleted_log_msg)
            obj.delete()
    else:
        return delete_selected_(modeladmin, request, queryset)


delete_selected.short_description = ugettext_lazy(
    "Delete selected %(verbose_name_plural)s")


def deactivate_selected(modeladmin, request, queryset):
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    if request.method == 'POST':

        for obj in queryset:
            user_deactivated_log_msg = f"""[User Deactivated]
            User: {request.user.username}
            Deactivated user with username: {obj.username} from IP Address {get_client_ip(request)}"""
            if not obj.is_active:
                continue
            if 'MyUser' in modeladmin.__str__():
                DELETED_USERS_LOGGER.debug(user_deactivated_log_msg)
            else:
                DELETED_GROUPS_LOGGER.debug(user_deactivated_log_msg)
            obj.is_active = False
            obj.save()
    else:
        return deactivate_selected(modeladmin, request, queryset)


deactivate_selected.short_description = ugettext_lazy(
    "Deactivate selected %(verbose_name_plural)s")


def activate_selected(modeladmin, request, queryset):
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    if request.method == 'POST':
        for obj in queryset:
            user_activated_log_msg = f"""[User Activated]
            User: {request.user.username}
            Activated user with username: {obj.username} from IP Address {get_client_ip(request)}"""
            if obj.is_active:
                continue
            if 'MyUser' in modeladmin.__str__():
                CREATED_USERS_LOGGER.debug(user_activated_log_msg)
            else:
                CREATED_USERS_LOGGER.debug(user_activated_log_msg)
            obj.is_active = True
            obj.save()

    else:
        return None


activate_selected.short_description = ugettext_lazy(
    "Activate selected %(verbose_name_plural)s")


class UserAccountAdmin(UserAdmin):
    actions = (delete_selected, deactivate_selected, activate_selected)
    list_display = ('username', 'first_name',
                    'last_name', 'email', 'is_active')
    filter_horizontal = ('groups',)

    def get_list_display(self, request):
        list_display = super(UserAccountAdmin, self).get_list_display(request)
        if request.user.is_superuser:
            list_display = ('username', 'first_name', 'last_name', 'email',
                            'groups', 'is_active', 'user_type')
            return list_display
        return list_display

    def get_form(self, request, obj=None, **kwargs):
        userform = super(UserAccountAdmin, self).get_form(
            request, obj=obj, **kwargs)
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
                perm_fields = ('is_active', 'is_staff',
                               'is_superuser', 'parent')

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


class MakerAdmin(UserAccountAdmin):
    add_form = MakerCreationAdminForm

    def save_model(self, request, obj, form, change):
        # TODO : FIX Parent hierarchy
        if request.user.is_superuser:
            obj.hierarchy = form.cleaned_data['parent'].hierarchy
        else:
            obj.hierarchy = request.user.hierarchy

        if obj.pk is not None:
            MODIFIED_USERS_LOGGER.debug(f"""[Maker User Modified]
            User: {request.user.username}
            Modified user with username: {obj.username} from IP Address {get_client_ip(request)}""")

        else:
            CREATED_USERS_LOGGER.debug(f"""[Maker User Created]
            User: {request.user.username}
            Created new maker with username: {obj.username}""")
        obj.save()


class CheckerAdmin(UserAccountAdmin):
    add_form = CheckerCreationAdminForm

    def save_model(self, request, obj, form, change):
        # TODO : FIX Parent hierarchy
        if request.user.is_superuser:
            obj.hierarchy = form.cleaned_data['parent'].hierarchy
        else:
            obj.hierarchy = request.user.hierarchy

        if obj.pk is not None:
            MODIFIED_USERS_LOGGER.debug(f"""[Checker User Modified]
            User: {request.user.username}
            Modified user with username: {obj.username} from IP Address {get_client_ip(request)}""")
        else:
            CREATED_USERS_LOGGER.debug(f"""[Checker User Created]
            User: {request.user.username}
            Created new checker with username: {obj.username}""")
        obj.save()


class InstantAPICheckerAdmin(UserAccountAdmin):
    add_form = MakerCreationAdminForm

    def save_model(self, request, obj, form, change):
        # TODO : FIX Parent hierarchy
        if request.user.is_superuser:
            obj.hierarchy = form.cleaned_data['parent'].hierarchy
        else:
            obj.hierarchy = request.user.hierarchy

        if obj.pk is not None:
            MODIFIED_USERS_LOGGER.debug(f"""[Instant Checker User Modified]
            User: {request.user.username}
            Modified user with username: {obj.username} from IP Address {get_client_ip(request)}""")

        else:
            CREATED_USERS_LOGGER.debug(f"""[Instant Checker User Created]
            User: {request.user.username}
            Created new maker with username: {obj.username}""")
        obj.save()


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


admin.site.register(RootUser, RootAdmin)
admin.site.register(MakerUser, MakerAdmin)
admin.site.register(CheckerUser, CheckerAdmin)
admin.site.register(SuperAdminUser, SuperAdmin)
admin.site.register(User)
admin.site.register(Client)
admin.site.register(InstantAPICheckerUser, InstantAPICheckerAdmin)
