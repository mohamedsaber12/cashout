from django.contrib import admin
from .models import Merchant,FileLegalDocs,FileLegalDocsForm
from django.utils.html import format_html
from django.urls import reverse

class InlineFile(admin.StackedInline):
    form = FileLegalDocsForm
    model= FileLegalDocs
    can_delete = True
    extra = 1

    def Download(self, instance):
        url = reverse('merchant:download_file',
                      args=(instance.id,))
        return format_html(u'<button type="button"><a href="{}">Download</a></button>', url)
    readonly_fields = ('Download', 'verified_by')
@admin.register(FileLegalDocs)
class FilelLegalDocsAdmin(admin.ModelAdmin):
    model= FileLegalDocs
    form = FileLegalDocsForm

    def save_model(self, request, obj, form, change):
        if obj.verified == True:
            obj.verified_by = request.user
        obj.save()



@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    def client_name(self, obj):
        return f'{obj.merchant.client}'

    list_display = ['client_name',]
    list_display_links = ['client_name']
    list_filter = ['merchant__client',]
    search_fields = ['merchant',]
    inlines = [InlineFile]
    
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if instance.verified == True:
                instance.verified_by = request.user
            instance.save()
        formset.save_m2m()
    
    