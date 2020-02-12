import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import AbstractBaseTransaction
from users.models import InstantAPICheckerUser


class InstantTransaction(AbstractBaseTransaction):
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
        null=True,
        on_delete=models.CASCADE,
        blank=True,
        related_name=_("instant_transaction"),
        verbose_name=_("Instant API Checker")
    )
    anon_sender = models.CharField(
        _("Sender - Agent"), max_length=14, blank=True, null=True
    )

    failure_reason = models.TextField(
            _("Failure reason"), blank=True, null=True
    )

    # Not needed fields
    updated_at = None
    TRANSACTION_TYPE_CHOICES = None
    to_user = None
    external_reference_1 = None
    external_reference_2 = None
    external_reference_3 = None
    external_reference_4 = None
    transaction_type = None

    class Meta:
        verbose_name = "Instant Transaction"
        verbose_name_plural = "Instant Transactions"
        get_latest_by = "-created_at"
        ordering = ["-created_at"]
