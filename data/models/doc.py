from __future__ import unicode_literals

import os

from django.conf import settings
from django.db import models
from django.urls import reverse

from data.utils import pkgen, update_filename


class Doc(models.Model):
    id = models.CharField(primary_key=True, editable=False,
                          unique=True, db_index=True, max_length=32, default=pkgen)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.CASCADE, related_name='doc')
    file_category = models.ForeignKey(
        'data.FileCategory', null=True, on_delete=models.CASCADE)
    file = models.FileField(upload_to=update_filename,
                            null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_disbursed = models.BooleanField(default=False)
    can_be_disbursed = models.BooleanField(default=False)
    is_processed = models.BooleanField(default=False)
    txn_id = models.CharField(max_length=16, null=True, blank=True)
    processing_failure_reason = models.CharField(max_length=256, null=True)

    class Meta:
        permissions = (("upload_file", "upload file"),
                       ("delete_file", "delete file"),
                       ("download_file_xlsx", "download xlsx file"),
                       ("access_file", "access file"),
                       ("download_file_txt", "download txt file"),
                       ("edit_file_online", "Edit the file online"),
                       ("process_file", "Can user process file data"),
                       ("can_disburse", "Can disburse file data"),
                       )
        verbose_name_plural = 'Documents'
        ordering = ('created_at', )

    def delete(self, *args, **kwargs):
        try:
            os.remove(os.path.join(settings.MEDIA_ROOT, self.file.name))
        except:
            pass
        super(Doc, self).delete(*args, **kwargs)

    def filename(self):
        return os.path.basename(self.file.name)

    def unique_field(self):
        return self.file_category.unique_field

    @property
    def count_doc_related(self):
        return self.file_category.doc.count()

    def get_doc_view_url(self):
        return reverse("data:doc_viewer", kwargs={'doc_id': self.id})
