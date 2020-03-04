from django.contrib import admin

from .forms import FileCategoryForm
from .models import Doc, DocReview, FileCategory
from .models import CollectionData, Format, FileData


class DocReviewAdmin(admin.ModelAdmin):
    """
    Admin class for tweaking the DocReview model at the admin panel
    """
    readonly_fields = ["doc", "user_created", "comment", "timestamp"]


class FileCategoryAdmin(admin.ModelAdmin):
    form = FileCategoryForm

    def get_form(self, request, obj=None, **kwargs):
        FileCategoryForm = super(FileCategoryAdmin, self).get_form(request, obj=obj, **kwargs)
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
    list_filter = (('created_at'),)
    readonly_fields = ('file',)
    list_display = ('filename', 'owner', 'type_of', 'created_at')

    def has_add_permission(self, request):
        return False


class FileDataAdmin(admin.ModelAdmin):
    list_filter     = ('date', 'user')
    list_display    = ('doc', 'user')
    readonly_fields = ('doc', 'data')

    def has_add_permission(self, request):
        return False


class FormatAdmin(admin.ModelAdmin):
    list_filter = ('hierarchy',)

    def has_add_permission(self, request):
        return False


# TODO: Add logs for deleting and adding any instance
admin.site.register(DocReview, DocReviewAdmin)
admin.site.register(Doc, DocAdmin)
admin.site.register(FileCategory, FileCategoryAdmin)
admin.site.register(Format, FormatAdmin)
admin.site.register(FileData, FileDataAdmin)
admin.site.register(CollectionData)
