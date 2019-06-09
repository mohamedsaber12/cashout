# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.core.exceptions import FieldError

from disb.models import Agent, VMTData



class VMTDataAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        try:
            if request.user.root.vmt:
                return False
        except VMTData.DoesNotExist:
            return super(VMTDataAdmin, self).has_add_permission(request)


admin.site.register(Agent)
admin.site.register(VMTData, VMTDataAdmin)
