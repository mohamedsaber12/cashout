# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from disbursement.models import DisbursementDocData
from users.models import CheckerUser

from ..utils import pkgen, update_filename


class Doc(models.Model):
    """
    Model for representing uploaded document object
    """
    DISBURSEMENT = 1
    COLLECTION = 2
    types = (
        (DISBURSEMENT, 'DISBURSEMENT'),
        (COLLECTION, 'COLLECTION')
    )

    id = models.CharField(primary_key=True, editable=False, unique=True, db_index=True, max_length=32, default=pkgen)
    file = models.FileField(upload_to=update_filename, null=True, blank=True)
    is_disbursed = models.BooleanField(default=False)
    can_be_disbursed = models.BooleanField(default=False)
    is_processed = models.BooleanField(default=False)
    txn_id = models.CharField(max_length=16, null=True, blank=True)
    processing_failure_reason = models.CharField(max_length=256, null=True)
    total_amount = models.FloatField(default=False)
    total_count = models.PositiveIntegerField(default=False)
    type_of = models.PositiveSmallIntegerField(default=DISBURSEMENT, choices=types)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doc')
    disbursed_by = models.ForeignKey("users.CheckerUser", on_delete=models.CASCADE, related_name='document', null=True)
    file_category = models.ForeignKey('data.FileCategory', on_delete=models.SET_NULL, related_name='doc', null=True)
    format = models.ForeignKey('data.Format', on_delete=models.DO_NOTHING, null=True)
    collection_data = models.ForeignKey(
            'data.CollectionData',
            on_delete=models.CASCADE,
            related_name='collection_doc',
            null=True
    )

    class Meta:
        permissions = (
            ("upload_file", "upload file"),
            ("delete_file", "delete file"),
            ("download_file_xlsx", "download xlsx file"),
            ("access_file", "access file"),
            ("download_file_txt", "download txt file"),
            ("edit_file_online", "Edit the file online"),
            ("process_file", "Can user process file data"),
            ("can_disburse", "Can disburse file data"),
        )
        verbose_name_plural = 'Documents'
        ordering = ('-created_at', )

    def __str__(self):
        """String representation for doc model objects"""
        return self.file.name

    def delete(self, *args, **kwargs):
        """
        :return: Delete document file if it exists at the file system specifically at the MEDIA ROOT directory
        """
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
        Check if checker can disburse current document(self) or not.
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
        """
        :return: disbursement success percentage
        """
        if not self.is_processed or not self.can_be_disbursed:
            return 0
        disbursement_data_count = self.disbursement_data.count()
        if disbursement_data_count == 0:
            return 0

        failed_disbursement_count = self.disbursement_data.filter(is_disbursed=False).count()
        success_percentage = ((disbursement_data_count-failed_disbursement_count) * 100) / disbursement_data_count
        success_percentage = round(success_percentage, 2) if success_percentage != 0 else 0

        return success_percentage

    def can_user_review(self, checker):
        """
        return tuple
        (can_user_review, user_already_reviewed)
        """
        if self.reviews.filter(user_created=checker).exists():
            return False, True
        reviews = self.reviews.all()

        can_review = False
        levels = CheckerUser.objects.filter(
                hierarchy=checker.hierarchy
        ).values_list('level__level_of_authority', flat=True)
        levels = list(set(levels))
        checker_level = checker.level.level_of_authority
        if min(levels) == checker_level:
            can_review = True
        else:
            levels = [level for level in levels if level < checker_level]
            levels = [max(levels, default=0), checker_level]
            if reviews.filter(user_created__level__level_of_authority__in=levels):
                can_review = True

        return can_review, False

    def is_reviews_completed(self):
        return self.reviews.filter(is_ok=True).count() >= self.file_category.no_of_reviews_required

    def is_reviews_rejected(self):
        return self.reviews.filter(is_ok=False).count() != 0

    def mark_uploaded_successfully(self):
        """Mark disbursement document status as uploaded successfully"""
        DisbursementDocData.objects.create(doc=self, doc_status=DisbursementDocData.UPLOADED_SUCCESSFULLY)

    def processed_successfully(self):
        """Mark disbursement document as processed successfully if it passed tests"""
        self.disbursement_txn.mark_doc_status_processed_successfully()
        self.is_processed = True
        self.save()

    def processing_failure(self, failure_reason):
        """
        Mark disbursement document as not processed successfully as it didn't pass tests
        :param failure_reason: Reason made this document didn't pass processing phase
        """
        self.disbursement_txn.mark_doc_status_processing_failure()
        self.is_processed = False
        self.processing_failure_reason = _(failure_reason)
        self.save()

    def mark_disbursement_failure(self):
        """Mark disbursement document disbursement status as failed"""
        self.disbursement_txn.mark_doc_status_disbursement_failure()

    def mark_disbursed_successfully(self, disburser, transaction_id, transaction_status):
        """
        Mark disbursement document as disbursed successfully
        :param disburser: Checker user who tried to disburse this document
        :param transaction_id: transaction id from the disburse response
        :param transaction_status: transaction status from the disburse response
        """
        self.disbursement_txn.mark_doc_status_disbursed_successfully(transaction_id, transaction_status)
        self.is_disbursed = True
        self.disbursed_by = disburser
        self.save()

    @property
    def validation_process_is_running(self):
        """:return True if doc is uploaded successfully"""
        return self.disbursement_txn.doc_status == DisbursementDocData.UPLOADED_SUCCESSFULLY

    @property
    def validated_successfully(self):
        """:return True if doc is processed successfully"""
        return self.disbursement_txn.doc_status == DisbursementDocData.PROCESSED_SUCCESSFULLY

    @property
    def validation_failed(self):
        """:return True if doc is processed failure is happened"""
        return self.disbursement_txn.doc_status == DisbursementDocData.PROCESSING_FAILURE

    @property
    def disbursed_successfully(self):
        """:return True if doc is disbursed successfully"""
        return self.disbursement_txn.doc_status == DisbursementDocData.DISBURSED_SUCCESSFULLY

    @property
    def disbursement_failed(self):
        """:return True if doc is disbursement failure happened"""
        return self.disbursement_txn.doc_status == DisbursementDocData.DISBURSEMENT_FAILURE

    @property
    def waiting_disbursement(self):
        """:return True if doc ready for disbursement after notifying checkers"""
        return self.can_be_disbursed and not self.disbursed_successfully and not self.disbursement_failed

    @property
    def has_callback(self):
        """:return True if doc has disbursement callback"""
        return self.disbursement_txn.has_callback

    @property
    def waiting_disbursement_callback(self):
        """:return True if doc disbursed successfully and the waits for the callback from the wallets side"""
        return self.disbursed_successfully and not self.has_callback
