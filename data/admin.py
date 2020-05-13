# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .forms import FileCategoryForm
from .models import Doc, DocReview, FileCategory


@admin.register(Doc)
class DocAdmin(admin.ModelAdmin):
    """
    Admin manager for the Doc model
    """

    list_display = ['filename', 'owner', 'type_of', 'is_processed', 'is_disbursed', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['file']

    def has_add_permission(self, request):
        return False


@admin.register(DocReview)
class DocReviewAdmin(admin.ModelAdmin):
    """
    Admin class for tweaking the DocReview model at the admin panel
    """

    list_display = ['doc', 'user_created', 'is_ok', 'comment', 'timestamp']
    readonly_fields = list_display


@admin.register(FileCategory)
class FileCategoryAdmin(admin.ModelAdmin):
    """
    Customize admin panel view for FileCategory model
    """

    list_display = ['name', 'user_created', 'unique_field', 'amount_field', 'issuer_field', 'no_of_reviews_required']
    list_filter = ['user_created']

    form = FileCategoryForm

    def get_form(self, request, obj=None, **kwargs):
        FileCategoryForm = super(FileCategoryAdmin, self).get_form(request, obj=obj, **kwargs)
        FileCategoryForm.request = request
        if obj:
            FileCategoryForm.obj = obj
        return FileCategoryForm

    def save_model(self, request, obj, form, change):
        # ToDo: Bug: Crash at editing record at admin panel
        instance = form.save(commit=False)
        user = request.user

        if not change or not instance.user_created:
            instance.user_created = user

            instance.save()
            form.save_m2m()
            obj.save()
        else:
            instance.save()

    def get_queryset(self, request):
        super(FileCategoryAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return FileCategory.objects.all()

        return FileCategory.objects.filter(user_created=request.user)


# @admin.register(FileData)
class FileDataAdmin(admin.ModelAdmin):
    list_filter = ['date', 'user']
    list_display = ['doc', 'user']
    readonly_fields = ['doc', 'data']

    def has_add_permission(self, request):
        return False


# @admin.register(Format)
class FormatAdmin(admin.ModelAdmin):
    list_filter = ['hierarchy']

    def has_add_permission(self, request):
        return False


# TODO: Add logs for deleting and adding any instance
# admin.site.register(CollectionData)
