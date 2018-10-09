import datetime
import logging

from django.contrib import admin
from django.contrib.admin.actions import delete_selected as delete_selected_
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext as _, ugettext_lazy

from data.utils import get_client_ip
from users.forms import UserForm, UserChangeForm
from users.models import User

CREATED_USERS_LOGGER = logging.getLogger("created_users")
DELETED_USERS_LOGGER = logging.getLogger("delete_users")
GROUP_CREATION_LOGGER = logging.getLogger("create_groups")
DELETED_GROUPS_LOGGER = logging.getLogger("delete_groups")
admin.site.unregister(Group)


# TODO: I need to check querysets for all for children
# TODO: Add logs for deleting and adding any instance

def delete_selected(modeladmin, request, queryset):
    if not modeladmin.has_delete_permission(request):
        raise PermissionDenied
    if request.POST.get('post'):
        for obj in queryset:
            now = datetime.datetime.now()
            if 'MyUser' in modeladmin.__str__():
                DELETED_USERS_LOGGER.debug(
                    'User Deleted at %s by %s from IP Address %s' % (
                        now, obj.username, get_client_ip(request)))
            else:
                DELETED_GROUPS_LOGGER.debug(
                    'User Deleted at %s by %s from IP Address %s' % (
                        now, obj.username, get_client_ip(request)))
            obj.delete()
    else:
        return delete_selected_(modeladmin, request, queryset)


delete_selected.short_description = ugettext_lazy("Delete selected %(verbose_name_plural)s")


def deactivate_selected(modeladmin, request, queryset):
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    if request.method == 'POST':

        for obj in queryset:
            if not obj.is_active:
                continue
            now = datetime.datetime.now()
            if 'MyUser' in modeladmin.__str__():
                DELETED_USERS_LOGGER.debug(
                    'User Deactivated at %s by %s from IP Address %s' % (
                        now, obj.username, get_client_ip(request)))
            else:
                DELETED_GROUPS_LOGGER.debug(
                    'User Deactivated at %s by %s from IP Address %s' % (
                        now, obj.name, get_client_ip(request)))
            obj.is_active = False
            obj.save()
    else:
        return deactivate_selected(modeladmin, request, queryset)


deactivate_selected.short_description = ugettext_lazy("Deactivate selected %(verbose_name_plural)s")


def activate_selected(modeladmin, request, queryset):
    if not modeladmin.has_change_permission(request):
        raise PermissionDenied
    if request.method == 'POST':
        for obj in queryset:
            if obj.is_active:
                continue
            now = datetime.datetime.now()
            if 'MyUser' in modeladmin.__str__():
                CREATED_USERS_LOGGER.debug(
                    'User Activated at %s by %s from IP Address %s' % (
                        now, obj.username, get_client_ip(request)))
            else:
                CREATED_USERS_LOGGER.debug(
                    'User Activated at %s by %s from IP Address %s' % (
                        now, obj.name, get_client_ip(request)))
            obj.is_active = True
            obj.save()

    else:
        return None


activate_selected.short_description = ugettext_lazy("Activate selected %(verbose_name_plural)s")


class UserAccountAdmin(UserAdmin):
    actions = (delete_selected, deactivate_selected, activate_selected)
    list_display = ('username', 'first_name', 'last_name', 'email', 'is_active')
    add_form = UserForm
    filter_horizontal = ('groups',)

    def get_list_display(self, request):
        list_display = super(UserAccountAdmin, self).get_list_display(request)
        if request.user.is_superuser:
            list_display = ('username', 'first_name', 'last_name', 'email',
                            'groups', 'is_active', 'user_type')
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

    def save_model(self, request, obj, form, change):
        if obj.pk is not None:
            CREATED_USERS_LOGGER.debug(
                'User with id %d has modified at %s from IP Address %s' % (
                    obj.pk, datetime.datetime.now(), get_client_ip(request)))

        else:
            now = datetime.datetime.now()
            CREATED_USERS_LOGGER.debug(
                'user created at %s %s' % (now, obj.username))

        obj.save()

    def get_fieldsets(self, request, obj=None):
        perm_fields = ('is_active', 'is_staff', 'bills_groups')
        if not obj:
            if request.user.is_superuser:
                perm_fields = ('is_active', 'is_staff', 'is_superuser',
                               'bills_groups', 'user_type')

            self.add_fieldsets = (
                (None, {
                    'classes': ('wide',),
                    'fields': ('username', 'password1', 'password2',)}
                 ),
                (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'mobile_no', 'arabic_name')}),
                (_('Permissions'), {'fields': perm_fields}),
                (_('Important dates'), {'fields': ('last_login', 'date_joined')})
            )

        elif obj:
            perm_fields = ('is_active', 'is_staff', 'bills_groups', 'user_type')
            self.add_fieldsets = (
                (None, {
                    'classes': ('wide',),
                    'fields': ('username', 'email', 'password')}
                 ),
                (_('Personal info'), {'fields': ('first_name', 'last_name', 'mobile_no', 'arabic_name')}),
                (_('Permissions'), {'fields': perm_fields}),
                (_('Important dates'), {'fields': ('last_login', 'date_joined')})
            )

        return self.add_fieldsets

    def get_queryset(self, request):
        qs = super(UserAccountAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        elif request.user.is_parent:
            qs = qs.filter(hierarchy=request.user.hierarchy)
            return qs
        else:
            return request.user.brothers()

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == 'bills_groups':
            qs = self._filter_groups(request)
            kwargs['queryset'] = qs
        return super(UserAccountAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)


admin.site.register(User, UserAccountAdmin)
