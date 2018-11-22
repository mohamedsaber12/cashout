from daterange_filter.filter import DateRangeFilter
from django.contrib import admin

from data.forms import FileCategoryForm, FileDocumentForm
from data.models import Doc, DocReview, FileCategory

# TODO: Add logs for deleting and adding any instance
admin.site.register(DocReview)


class FileCategoryAdmin(admin.ModelAdmin):
    form = FileCategoryForm

    def get_form(self, request, obj=None, **kwargs):
        FileCategoryForm = super(FileCategoryAdmin, self).get_form(
            request, obj=obj, **kwargs)
        FileCategoryForm.request = request
        if obj:
            FileCategoryForm.obj = obj
        return FileCategoryForm

    def save_model(self, request, obj, form, change):
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


class DocAdmin(admin.ModelAdmin):
    form = FileDocumentForm
    list_filter = (('created_at', DateRangeFilter),)
    readonly_fields = ('file',)
    list_display = ('filename', 'owner', 'file_category', 'created_at')

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        qs = super(DocAdmin, self).get_queryset(request)
        return qs.filter(owner__hierarchy=request.user.hierarchy)

    def get_form(self, request, obj=None, **kwargs):
        DocumentForm = super(DocAdmin, self).get_form(
            request, obj=obj, **kwargs)
        DocumentForm.request = request
        return DocumentForm


admin.site.register(Doc, DocAdmin)
admin.site.register(FileCategory, FileCategoryAdmin)
