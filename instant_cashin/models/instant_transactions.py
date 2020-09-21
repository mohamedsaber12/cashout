import uuid

from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from django.utils.translation import gettext_lazy as _

from core.models import AbstractBaseTransaction
from users.models import InstantAPICheckerUser


class AbstractBaseIssuer(models.Model):
    """
    Base Issuer model.
    """

    # Issuer choices
    VODAFONE = "V"
    ETISALAT = "E"
    ORANGE = "O"
    AMAN = "A"
    ISSUER_TYPE_CHOICES = [
        (VODAFONE, _("Vodafone")),
        (ETISALAT, _("Etisalat")),
        (ORANGE, _("Orange")),
        (AMAN, _("Aman")),
    ]

    issuer_type = models.CharField(
            _("Issuer Type"),
            max_length=20,
            choices=ISSUER_TYPE_CHOICES,
            blank=True,
            null=True,
            db_index=True,
    )

    class Meta:
        abstract = True


class InstantTransaction(AbstractBaseTransaction, AbstractBaseIssuer):
    """
    Model for instant transactions
    """

    uid = models.UUIDField(
            default=uuid.uuid4,
            editable=False,
            unique=True,
            primary_key=True,
            verbose_name=_("Transaction Reference")
    )
    from_user = models.ForeignKey(
        InstantAPICheckerUser,
        db_index=True,
        null=True,
        on_delete=models.CASCADE,
        blank=True,
        related_name=_("instant_transaction"),
        verbose_name=_("Instant API Checker")
    )
    anon_sender = models.CharField(
            _("Sender"),
            db_index=True,
            max_length=14,
            blank=True,
            null=True,
            help_text=_("Agent used from Root's agents list")
    )
    failure_reason = models.TextField(
            _("Failure reason"),
            blank=True,
            null=True,
            help_text=_("Empty if transaction status is Successful")
    )
    aman_obj = GenericRelation(
            "instant_cashin.AmanTransaction",
            object_id_field="transaction_id",
            content_type_field="transaction_type",
            related_query_name="aman_instant"
    )

    # Not needed fields
    to_user = None
    external_reference_1 = None
    external_reference_2 = None
    external_reference_3 = None
    external_reference_4 = None
    transaction_type = None

    class Meta:
        verbose_name = "Instant Transaction"
        verbose_name_plural = "Instant Transactions"
        get_latest_by = "-updated_at"
        ordering = ["-created_at", "-updated_at"]

    def mark_pending(self):
        """Mark transaction status as pending"""
        self.status = self.PENDING
        self.save()

    def mark_failed(self, failure_reason=""):
        """
        Mark transaction status as failed and add the failure reason if provided
        :param failure_reason: if provided add failure reason
        """
        if failure_reason: self.failure_reason = failure_reason
        self.status = self.FAILED
        self.save()

    @property
    def aman_transaction(self):
        """Property for retrieving aman object details for transaction records made through Aman"""
        try:
            return self.aman_obj.first()
        except AttributeError:
            return None
