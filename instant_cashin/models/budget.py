from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import AbstractTimeStamp


class Budget(AbstractTimeStamp):
    """
    Model for checking budget before executing disbursement
    """

    max_amount = models.IntegerField(_("Max Allowed Amount"), default=0, null=False, blank=False)
    disbursed_amount = models.IntegerField(_("Disbursed Amount"), default=0, null=False, blank=False)
    total_disbursed_amount = models.IntegerField(
            _("Total Previously Disbursed Amount"),
            default=0,
            null=False,
            blank=False
    )
    disburser = models.OneToOneField(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name='budget',
            verbose_name=_("Disburser"),
            help_text=_("Before every cashin transaction, "
                        "amount to be disbursed will be validated against this checker's budget limit")
    )
    created_by = models.ForeignKey(
            "users.SuperAdminUser",
            on_delete=models.CASCADE,
            null=True,
            related_name='budget_creator',
            verbose_name=_("Maintainer Admin"),
            help_text=_("Admin who created/updated this budget values")
    )

    class Meta:
        verbose_name = "Allowed Budget"
        verbose_name_plural = "Allowed Budgets"
        get_latest_by = "-updated_at"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.disburser.username} Budget"

    def within_threshold(self, amount_to_be_disbursed):
        """
        Check if the amount to be disbursed plus the previously disbursed amount won't exceed the max_amount
        :param amount_to_be_disbursed: Amount to be disbursed at the currently running transaction
        :return: True/False
        """
        new_amount = int(self.disbursed_amount) + int(amount_to_be_disbursed)

        if not int(new_amount) <= int(self.max_amount):
            return False
        return True

    def update_disbursed_amount(self, amount):
        """
        Update the total disbursement amount at each successful transaction
        :param amount: the amount to be disbursed
        :return: True/False
        """
        if not self.within_threshold(amount):
            return False

        self.total_disbursed_amount += int(amount)
        self.disbursed_amount += int(amount)
        self.save()
        return True
