# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os, uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from core.models import AbstractBaseStatus
from disbursement.models import DisbursementDocData, BankTransaction
from users.models import CheckerUser
from utilities.models import AbstractBaseDocType, SoftDeletionModel

from ..utils import update_filename


class Doc(AbstractBaseDocType, SoftDeletionModel):
    """
    Model for representing uploaded document object
    """

    id = models.CharField(
        primary_key=True, editable=False, unique=True, db_index=True,
        max_length=36, default=uuid.uuid4
    )
    file = models.FileField(upload_to=update_filename, null=True, blank=True)
    is_disbursed = models.BooleanField(default=False)
    can_be_disbursed = models.BooleanField(default=False)
    is_processed = models.BooleanField(default=False)
    txn_id = models.CharField(max_length=16, null=True, blank=True)
    processing_failure_reason = models.CharField(max_length=256, null=True)
    total_amount = models.FloatField(default=False)
    total_amount_with_fees_vat = models.DecimalField(
            _("Total amount plus fees and VAT"),
            max_digits=10,
            decimal_places=2,
            default=0,
            null=True,
            blank=True
    )
    total_count = models.PositiveIntegerField(default=False)
    has_change_profile_callback = models.BooleanField(default=False, verbose_name=_('Has change profile callback?'))
    owner = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name='doc',
            verbose_name=_("Owner/Maker")
    )
    disbursed_by = models.ForeignKey(
            "users.CheckerUser",
            on_delete=models.CASCADE,
            related_name='document',
            verbose_name=_("Disbursed by/Checker"),
            null=True
    )
    format = models.ForeignKey('data.Format', on_delete=models.DO_NOTHING, null=True)
    file_category = models.ForeignKey(
            'data.FileCategory',
            on_delete=models.SET_NULL,
            related_name='doc',
            null=True,
            blank=True
    )
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
        return reverse("data:doc_viewer", kwargs={'doc_id': self.id})

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
            if self.is_e_wallet:
                reviews_required = self.file_category.no_of_reviews_required
            else:
                all_categories = self.owner.root.file_category.all()
                reviews_required = min([cat.no_of_reviews_required for cat in all_categories])

            if not checker.is_vodafone_default_onboarding and not checker.is_banks_standard_model_onboaring:
                if self.is_e_wallet:
                    within_threshold = True if self.total_amount_with_fees_vat <= checker.root.budget.current_balance \
                        else False
                elif self.is_bank_wallet:
                    within_threshold = checker.root.budget.within_threshold(self.total_amount, "bank_wallet")
                else:
                    within_threshold = checker.root.budget.within_threshold(self.total_amount, "bank_card")

                if not within_threshold:
                    reason = _("File's total amount exceeds your current balance, please contact your support team")
                    code = 5
                    return False, reason, code

            if self.can_be_disbursed and reviews.filter(is_ok=False).count() == 0:
                if reviews.filter(is_ok=True).count() >= reviews_required:
                    if checker.level.max_amount_can_be_disbursed >= self.total_amount:
                        return True, reason, 0
                    else:
                        reason = _(
                                f"Not Permitted to disburse because the file's total amount exceeds your "
                                   f"maximum amount that can be disbursed, please contact your support team"
                        )
                        code = 3
                else:
                    reason = _("Document is still suspended due to shortage of checking")
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

        # 1. Calculate the success disbursement ratio of e-wallets docs
        if self.is_e_wallet:
            disbursement_data_count = self.disbursement_data.count()
            if disbursement_data_count == 0:
                return 0

            failed_disbursement_count = self.disbursement_data.filter(is_disbursed=False).count()
            success_percentage = ((disbursement_data_count-failed_disbursement_count) * 100) / disbursement_data_count
            success_percentage = round(success_percentage, 2) if success_percentage != 0 else 0

            return success_percentage

        # 2. Calculate the success disbursement ratio of bank wallets/cards docs
        elif self.is_bank_wallet or self.is_bank_card:
            if self.is_bank_wallet:
                doc_transactions = self.bank_wallets_transactions.all()
            else:
                bank_trx_ids = BankTransaction.objects.filter(document=self). \
                    order_by("parent_transaction__transaction_id", "-id"). \
                    distinct("parent_transaction__transaction_id"). \
                    values_list("id", flat=True)
                doc_transactions = BankTransaction.objects.filter(id__in=bank_trx_ids).order_by("-created_at")

            doc_transactions_count = doc_transactions.count()
            if doc_transactions_count == 0:
                return 0

            failed_transactions_count = doc_transactions.filter(~Q(status=AbstractBaseStatus.SUCCESSFUL)).count()
            success_percentage = ((doc_transactions_count-failed_transactions_count) * 100) / doc_transactions_count
            success_percentage = round(success_percentage, 2) if success_percentage != 0 else 0

            return success_percentage
        else:
            return 0

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
        if self.is_e_wallet:
            return self.reviews.filter(is_ok=True).count() >= self.file_category.no_of_reviews_required
        else:
            all_categories = self.owner.root.file_category.all()
            least_reviews_count = min([cat.no_of_reviews_required for cat in all_categories])
            return self.reviews.filter(is_ok=True).count() >= least_reviews_count

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

    @cached_property
    def is_e_wallet(self):
        return self.type_of == AbstractBaseDocType.E_WALLETS

    @cached_property
    def is_bank_wallet(self):
        return self.type_of == AbstractBaseDocType.BANK_WALLETS

    @cached_property
    def is_bank_card(self):
        return self.type_of == AbstractBaseDocType.BANK_CARDS
