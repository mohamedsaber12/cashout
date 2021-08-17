import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .utils.models import get_reverse_dict_from_choices


class AbstractTimeStamp(models.Model):
    """
    Time stamp class for updated_at and created_at fields.
    """

    created_at = models.DateTimeField(
        _("Created At"),
        auto_now_add=True,
        null=True,
        blank=True,
        db_index=True,
    )
    updated_at = models.DateTimeField(
        _("Updated At"), auto_now=True, null=True, blank=True, db_index=True
    )

    class Meta:
        abstract = True


class AbstractBaseUUID(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class AbstractBaseModel(AbstractTimeStamp, AbstractBaseUUID):
    """
    Base model with all of the common fields.
    """

    class Meta:
        abstract = True

    def __str__(self):
        return f"{str(self._meta.model_name).capitalize()}-{self.uid}"


class AbstractBaseModelNamed(models.Model):
    """
    Base model with all of the common fields, with name field.
    """

    name = models.CharField(_("Name"), max_length=500, unique=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.name if self.name else self.uid}"


class AbstractBaseStatus(models.Model):
    """
    Base Status model.
    """

    # choices
    SUCCESSFUL = "S"
    FAILED = "F"
    PENDING = "P"
    DEFAULT = "d"
    STATUS_CHOICES = [
        (SUCCESSFUL, _("Successful")),
        (FAILED, _("Failed")),
        (PENDING, _("Pending")),
        (DEFAULT, _("Default")),
    ]
    status = models.CharField(
        _("status"), max_length=1, choices=STATUS_CHOICES, default=DEFAULT
    )

    class Meta:
        abstract = True


class AbstractBaseServiceCharge(AbstractBaseModel):
    name = models.CharField(_("Name"), max_length=255, blank=True)
    percentage = models.FloatField(_("Percentage"), default=100.0)
    min_charge = models.FloatField(_("Min Charge"), default=0.0)
    max_charge = models.FloatField(_("Max Charge"), default=0.0)

    class Meta:
        abstract = True


class AbstractBaseTransaction(AbstractBaseModel, AbstractBaseStatus):
    TRANSACTION_TYPE_CHOICES = []
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.CASCADE,
        related_name=_("from_user_related"),
        blank=True,
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.CASCADE,
        related_name=_("to_user_related"),
        blank=True,
    )
    anon_sender = models.CharField(
        _("Anonymous Sender"), max_length=14, blank=True, null=True
    )
    anon_recipient = models.CharField(
        _("Anonymous Recipient"), max_length=14, blank=True, null=True
    )
    amount = models.FloatField(_("Amount"), default=0.0)
    transaction_type = models.CharField(
        _("Transaction Type"),
        max_length=50,
        choices=TRANSACTION_TYPE_CHOICES,
        blank=True,
        null=True,
        db_index=True,
    )
    external_reference_1 = models.CharField(
        _("External Reference 1"),
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
    )
    external_reference_2 = models.CharField(
        _("External Reference 2"),
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
    )
    external_reference_3 = models.CharField(
        _("External Reference 3"),
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
    )
    external_reference_4 = models.CharField(
        _("External Reference 4"),
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
    )

    def mark_successful(self):
        self.status = self.SUCCESSFUL
        self.save()

    def mark_failed(self):
        self.status = self.FAILED
        self.save()

    class Meta:
        abstract = True


class StatusChoicesReverseQueryModelAdminMixin(object):
    def lower_dict_keys(self, some_dict):
        """Convert all keys to lowercase"""
        result = {}
        for key, value in some_dict.items():
            try:
                result[key.lower()] = value
            except AttributeError:
                result[key] = value
        return result

    def get_search_results(self, request, queryset, search_term):
        """
        Adds ability to the admin class to search in the model
        by status type in both lower and upper case.
        """
        reverse_dict = get_reverse_dict_from_choices(
            AbstractBaseStatus.STATUS_CHOICES
        )
        reverse_dict = self.lower_dict_keys(reverse_dict)
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )
        try:
            search_term_as_str = str(search_term).lower()
        except ValueError:
            pass
        else:
            if search_term_as_str in reverse_dict:
                queryset |= self.model.objects.filter(
                    status=reverse_dict[search_term_as_str]
                )
        return queryset, use_distinct

