import uuid

from django.db import models
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

    def blank_anon_sender(self):
        self.anon_sender = ''
        self.save()
