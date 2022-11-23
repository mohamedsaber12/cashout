import os
from django.shortcuts import render
from django.views.generic import View
from merchants.models import FileLegalDocs
from django.http import HttpResponse
# Create your views here.
class DownloadFile(View):

    def get(self, request, file_id, *args, **kwargs):
        LegalDocs= FileLegalDocs.objects.filter(id=file_id).first()
        filename = os.path.basename(LegalDocs.file.name)
        response = HttpResponse(LegalDocs.file)
        response['Content-Disposition'] = \
        			f'attachment; filename={filename}'
        return response
        