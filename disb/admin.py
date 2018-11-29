# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.core.exceptions import FieldError

from disb.forms import AgentAdminForm
from disb.models import Agent, VMTData


class AgentAdmin(admin.ModelAdmin):
    form = AgentAdminForm

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('pin',)
        else:
            return ()

    def get_exclude(self, request, obj=None):
        exclude = super(AgentAdmin, self).get_exclude(request, obj)
        if request.user.is_superuser:
            return ()
        return exclude

    def get_queryset(self, request):
        try:
            hierarchy = request.user.hierarchy
            qs = super(AgentAdmin, self).get_queryset(request)
            return qs.filter(wallet_provider__hierarchy=hierarchy)
        except FieldError:
            return super(AgentAdmin, self).get_queryset(request)

    def save_form(self, request, form, change):
        instance = form.save(commit=False)
        if not change:
            instance.wallet_provider = request.user if request.user.is_root else request.user.root
            instance.set_pin(instance.pin)
        return instance


class VMTDataAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        try:
            if request.user.root.vmt:
                return False
        except VMTData.DoesNotExist:
            return super(VMTDataAdmin, self).has_add_permission(request)


admin.site.register(Agent, AgentAdmin)
admin.site.register(VMTData, VMTDataAdmin)
