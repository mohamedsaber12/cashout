# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.core.exceptions import FieldError

from disb.forms import AgentForm
from disb.models import Agent, VMTData


class AgentAdmin(admin.ModelAdmin):
    form = AgentForm

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
            instance.wallet_provider = request.user if request.user.is_parent else request.user.parent
            instance.set_pin(instance.pin)
        return instance


class VMTDataAdmin(admin.ModelAdmin):
    exclude = ('vmt',)

    def save_form(self, request, form, change):
        instance = form.save(commit=False)
        if not change:
            instance.vmt = request.user if request.user.is_parent else request.user.parent
        return instance

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        try:
            if request.user.parent.vmt:
                return False
        except VMTData.DoesNotExist:
            return super(VMTDataAdmin, self).has_add_permission(request)

    def get_queryset(self, request):
        try:
            hierarchy = request.user.hierarchy
            qs = super(VMTDataAdmin, self).get_queryset(request)
            return qs.filter(vmt__hierarchy=hierarchy)
        except FieldError:
            return super(VMTDataAdmin, self).get_queryset(request)

admin.site.register(Agent, AgentAdmin)
admin.site.register(VMTData, VMTDataAdmin)
