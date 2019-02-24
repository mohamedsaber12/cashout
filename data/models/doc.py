from __future__ import unicode_literals

import os

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from data.utils import pkgen, update_filename


class Doc(models.Model):
    DISBURSEMENT = 1
    COLLECTION = 2
    types = (
        (DISBURSEMENT, 'DISBURSEMENT'),
        (COLLECTION, 'COLLECTION')
    )
    id = models.CharField(primary_key=True, editable=False,
                          unique=True, db_index=True, max_length=32, default=pkgen)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.CASCADE, related_name='doc')
    file_category = models.ForeignKey(
        'data.FileCategory', null=True, on_delete=models.DO_NOTHING, related_name='doc')
    collection_data = models.ForeignKey(
        'data.CollectionData', null=True, on_delete=models.CASCADE, related_name='collection_doc')
    file = models.FileField(upload_to=update_filename,
                            null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_disbursed = models.BooleanField(default=False)
    disbursed_by = models.ForeignKey(
        "users.CheckerUser", on_delete=models.CASCADE, null=True, related_name='document')
    can_be_disbursed = models.BooleanField(default=False)
    is_processed = models.BooleanField(default=False)
    txn_id = models.CharField(max_length=16, null=True, blank=True)
    processing_failure_reason = models.CharField(max_length=256, null=True)
    total_amount = models.FloatField(default=False)
    total_count = models.PositiveIntegerField(default=False)
    type_of = models.PositiveSmallIntegerField(default=DISBURSEMENT, choices=types)
    format = models.ForeignKey('data.Format', on_delete=models.DO_NOTHING, null=True)

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

    def get_absolute_url(self):
        from django.urls import reverse
        if self.type_of == self.DISBURSEMENT:
            return reverse("data:doc_viewer", kwargs={'doc_id': self.id})
        else:
            return reverse("data:doc_collection_detail", kwargs={'pk': self.id})

    def get_delete_url(self):
        from django.urls import reverse
        return reverse("data:file_delete", kwargs={'pk': self.id})

    def can_user_disburse(self, checker):
        """"
        Check if checker can disburse current documemt(self) or not.
        return tuple:
        can disburse:boolean
        reason: reason why checker can not disburse 
        code: error code
        """
        reviews = self.reviews.all()
        reason = ''
        if checker.root.client.is_active:
            if self.can_be_disbursed and reviews.filter(is_ok=False).count() == 0:
                if reviews.filter(is_ok=True).count() >= self.file_category.no_of_reviews_required:
                    if checker.level.max_amount_can_be_disbursed >= self.total_amount:
                        return True, reason, 0
                    else:
                        reason = _("Not Permitted to disburse")
                        code = 3
                else:
                    reason = _("Document is still suspend due to shortage of checking")
                    code = 2
            else:
                reason = _("Issues are submitted by some users, please resolve any conflict first")
                code = 1
        else:
            reason = _("Your Entity is deactivated")
            code = 4
        return False, reason, code

    def disbursement_ratio(self):
        """return disbursement success percentage"""
        if not self.is_processed or not self.can_be_disbursed:
            return 0
        disbursement_data_count = self.disbursement_data.count()
        if disbursement_data_count == 0:
            return 0

        failed_disbursement_count = self.disbursement_data.filter(
            is_disbursed=False).count()
        success_percentage = (
            (disbursement_data_count-failed_disbursement_count) * 100) / disbursement_data_count
        success_percentage = round(
            success_percentage, 2) if success_percentage != 0 else 0
        return success_percentage


    def can_user_review(self,checker):
        """
        return tuple
        (can_user_review, user_already_reviewed)
        """
        if self.reviews.filter(user_created=checker).exists():
            return False, True
        reviews = self.reviews.all()
        return (checker.level.level_of_authority <= reviews.count()+1 , False)
        
    def is_reviews_completed(self):
        return self.reviews.filter(is_ok=True).count() >= self.file_category.no_of_reviews_required

    def is_reviews_rejected(self):
        return self.reviews.filter(is_ok=False).count() != 0 