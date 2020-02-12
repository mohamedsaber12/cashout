from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import pre_save
from django.utils.translation import gettext_lazy as _

from core.models import AbstractTimeStamp


class Budget(AbstractTimeStamp):
    """
    Model for checking budget before executing disbursement
    """

    disburser = models.OneToOneField(
            get_user_model(),
            on_delete=models.CASCADE,
            related_name='budget',
            verbose_name=_("Disburser"),
            help_text=_("Before every cashin transaction, "
                        "amount to be disbursed will be validated against checker's budget limit")
    )
    max_amount = models.IntegerField(_("Max Allowed Amount"), default=0, null=False, blank=False)
    disbursed_amount = models.IntegerField(_("Disbursed Amount"), default=0, null=False, blank=False)

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
        new_amount = self.disbursed_amount + amount_to_be_disbursed

        if not new_amount <= self.max_amount:
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

        self.disbursed_amount += amount
        self.save()
        return True


def budget_pre_save_receiver(instance, *args, **kwargs):
    pass
