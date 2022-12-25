# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal
import logging

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.models import AbstractTimeStamp
from simple_history.models import HistoricalRecords
from django.db import transaction


BUDGET_LOGGER = logging.getLogger("custom_budgets")


class CallWalletsModerator(models.Model):
    """
    Moderator to manage calls/requests to the wallets
    """

    disbursement = models.BooleanField(default=True)
    instant_disbursement = models.BooleanField(default=True)
    change_profile = models.BooleanField(default=True)
    set_pin = models.BooleanField(default=True)
    user_inquiry = models.BooleanField(default=True)
    balance_inquiry = models.BooleanField(default=True)
    user_created = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name=_("callwallets_moderator"),
        verbose_name=_("The moderator admin"),
    )

    class Meta:
        verbose_name = "Call Wallets Moderator"
        verbose_name_plural = "Call Wallets Moderators"
        ordering = ["-id"]

    def __str__(self):
        """String representation for the moderator model objects"""
        return f"{self.user_created.username} moderator"


class Budget(AbstractTimeStamp):
    """
    Model for handling entities balance/budget
    """

    disburser = models.OneToOneField(
        "users.RootUser",
        on_delete=models.CASCADE,
        related_name="budget",
        verbose_name=_("Owner/Admin of the Disburser"),
        help_text=_(
            "Before every cashin transaction, the amount to be disbursed "
            "will be validated against the current balance of the (API)-Checker owner"
        ),
    )
    created_by = models.ForeignKey(
        "users.SuperAdminUser",
        on_delete=models.CASCADE,
        related_name="budget_creator",
        verbose_name=_("Maintainer - Super Admin"),
        null=True,
        help_text=_("Super Admin who created/updated this budget values"),
    )
    current_balance = models.DecimalField(
        _("Current Balance"),
        max_digits=10,
        decimal_places=2,
        default=0,
        null=True,
        blank=True,
        help_text=_(
            "Updated automatically after any disbursement callback or any addition from add_new_amount"
        ),
    )
    total_disbursed_amount = models.DecimalField(
        _("Total Disbursed Amount"),
        max_digits=15,
        decimal_places=2,
        default=0,
        null=False,
        blank=False,
        help_text=_("Updated automatically after any disbursement callback"),
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Custom Budget"
        verbose_name_plural = "Custom Budgets"
        get_latest_by = "-updated_at"
        ordering = ["-created_at"]

    def __str__(self):
        """String representation for a custom budget object"""
        return f"{self.disburser.username} Custom Budget"

    def get_absolute_url(self):
        """Success form submit - object saving url"""
        return reverse(
            "utilities:budget_update", kwargs={"username": self.disburser.username}
        )

    def accumulate_amount_with_fees_and_vat(
        self, amount_to_be_disbursed, issuer_type, num_of_trns=1
    ):
        """Accumulate amount being disbursed with fees percentage and 14 % VAT"""
        actual_amount = round(Decimal(amount_to_be_disbursed), 2)

        # 1. Determine the type of the issuer to calculate the fees for
        if issuer_type == "vodafone" or issuer_type == "V" or issuer_type == "v":
            issuer_type_refined = FeeSetup.VODAFONE
        elif issuer_type == "etisalat" or issuer_type == "E" or issuer_type == "e":
            issuer_type_refined = FeeSetup.ETISALAT
        elif issuer_type == "orange" or issuer_type == "O" or issuer_type == "o":
            issuer_type_refined = FeeSetup.ORANGE
        elif issuer_type == "aman" or issuer_type == "A" or issuer_type == "a":
            issuer_type_refined = FeeSetup.AMAN
        elif issuer_type == "bank_card" or issuer_type == "C" or issuer_type == "c":
            issuer_type_refined = FeeSetup.BANK_CARD
        elif issuer_type == "bank_wallet" or issuer_type == "B" or issuer_type == "b":
            issuer_type_refined = FeeSetup.BANK_WALLET

        # 2. Pick the fees objects corresponding to the determined issuer type
        fees_obj = self.fees.filter(issuer=issuer_type_refined)
        fees_obj = fees_obj.first() if fees_obj.count() > 0 else None

        # 3. Calculate the fees for the passed amount to be disbursed using the picked fees type and value
        if fees_obj:
            if fees_obj.fee_type == FeeSetup.FIXED_FEE:
                fixed_value = fees_obj.fixed_value
                fees_aggregated_value = fixed_value * num_of_trns
            elif fees_obj.fee_type == FeeSetup.PERCENTAGE_FEE:
                percentage_value = fees_obj.percentage_value
                fees_aggregated_value = round(
                    ((actual_amount * percentage_value) / 100), 4
                )
            elif fees_obj.fee_type == FeeSetup.MIXED_FEE:
                fixed_value = fees_obj.fixed_value
                percentage_value = fees_obj.percentage_value
                fees_aggregated_value = (
                    round(((actual_amount * percentage_value) / 100), 4) + fixed_value
                )

            # 3.1 Check the total fees_aggregated_value if it complies against the min and max values
            if 0 < fees_obj.min_value > fees_aggregated_value:
                fees_aggregated_value = fees_obj.min_value

            if 0 < fees_obj.max_value < fees_aggregated_value:
                fees_aggregated_value = fees_obj.max_value

            vat_value = round(((fees_aggregated_value * Decimal(14.00)) / 100), 4)
            total_amount_with_fees_and_vat = round(
                (actual_amount + fees_aggregated_value + vat_value), 2
            )

            return total_amount_with_fees_and_vat
        else:
            raise ValueError(
                _(
                    f"Fees type and value for the passed issuer -{issuer_type}- does not exist!"
                )
            )

    def calculate_fees_and_vat_for_amount(
        self, amount_to_be_disbursed, issuer_type, num_of_trns=1
    ):
        """
        Calculate fees percentage and 14 % VAT regarding specific amount and issuer.
        TODO: Remove the repeated code via exporting the main part into a generic method
        """
        actual_amount = round(Decimal(amount_to_be_disbursed), 2)

        # 1. Determine the type of the issuer to calculate the fees for
        if issuer_type == "vodafone" or issuer_type == "V":
            issuer_type_refined = FeeSetup.VODAFONE
        elif issuer_type == "etisalat" or issuer_type == "E":
            issuer_type_refined = FeeSetup.ETISALAT
        elif issuer_type == "orange" or issuer_type == "O":
            issuer_type_refined = FeeSetup.ORANGE
        elif issuer_type == "aman" or issuer_type == "A":
            issuer_type_refined = FeeSetup.AMAN
        elif issuer_type == "bank_card" or issuer_type == "C":
            issuer_type_refined = FeeSetup.BANK_CARD
        elif issuer_type == "bank_wallet" or issuer_type == "B":
            issuer_type_refined = FeeSetup.BANK_WALLET
        elif issuer_type == "default" or issuer_type in ["D", "d"]:
            return 0, 0

        # 2. Pick the fees objects corresponding to the determined issuer type
        fees_obj = self.fees.filter(issuer=issuer_type_refined)
        fees_obj = fees_obj.first() if fees_obj.count() > 0 else None

        # 3. Calculate the fees for the passed amount to be disbursed using the picked fees type and value
        if fees_obj:
            if fees_obj.fee_type == FeeSetup.FIXED_FEE:
                fixed_value = fees_obj.fixed_value
                fees_value = fixed_value * num_of_trns
            elif fees_obj.fee_type == FeeSetup.PERCENTAGE_FEE:
                percentage_value = fees_obj.percentage_value
                fees_value = round(((actual_amount * percentage_value) / 100), 4)
            elif fees_obj.fee_type == FeeSetup.MIXED_FEE:
                fixed_value = fees_obj.fixed_value
                percentage_value = fees_obj.percentage_value
                fees_value = (
                    round(((actual_amount * percentage_value) / 100), 4) + fixed_value
                )

            # 3.1 Check the total fees_value if it complies against the min and max values
            if 0 < fees_obj.min_value > fees_value:
                fees_value = fees_obj.min_value

            if 0 < fees_obj.max_value < fees_value:
                fees_value = fees_obj.max_value

            vat_value = round(((fees_value * Decimal(14.00)) / 100), 4)
            return fees_value, vat_value
        else:
            raise ValueError(
                _(
                    f"Fees type and value for the passed issuer -{issuer_type}- does not exist!"
                )
            )

    def within_threshold(self, amount_to_be_disbursed, issuer_type):
        """
        Check if the amount to be disbursed won't exceed the current balance
        :param amount_to_be_disbursed: Amount to be disbursed at the currently running transaction
        :param issuer_type: Channel/Issuer used to disburse the amount over
        :return: True/False
        """
        try:
            amount_plus_fees_vat = self.accumulate_amount_with_fees_and_vat(
                amount_to_be_disbursed, issuer_type.lower()
            )

            if amount_plus_fees_vat <= round(self.current_balance, 2):
                return True
            return False
        except (ValueError, Exception) as e:
            raise ValueError(
                _(
                    f"Error while checking the amount to be disbursed if within threshold - {e.args}"
                )
            )

    def update_disbursed_amount_and_current_balance(
        self, amount, issuer_type, num_of_trns=1
    ):
        """
        Update the total disbursement amount and the current balance after each successful transaction
        :param amount: the amount being disbursed
        :param issuer_type: Channel/Issuer used to disburse the amount over
        :return: True/False
        """
        try:
            with transaction.atomic():
                budget_obj = Budget.objects.select_for_update().get(id=self.id)
                print("===============ATOMIC=================")
                amount_plus_fees_vat = budget_obj.accumulate_amount_with_fees_and_vat(
                    amount, issuer_type.lower(), num_of_trns
                )
                current_balance_before = budget_obj.current_balance
                applied_fees_and_vat = amount_plus_fees_vat - Decimal(amount)
                budget_obj.total_disbursed_amount += amount_plus_fees_vat
                budget_obj.current_balance -= amount_plus_fees_vat
                balance_after = budget_obj.current_balance
                budget_obj.save()
                BUDGET_LOGGER.debug(
                    f"[message] [CUSTOM BUDGET UPDATE] [{budget_obj.disburser.username}] -- disbursed amount: {amount}, "
                    f"applied fees plus VAT: {applied_fees_and_vat}, used issuer: {issuer_type.lower()}, "
                    f"current balance before: {current_balance_before}, current balance after: {budget_obj.current_balance}"
                )
        except Exception as e:
            raise ValueError(
                _(
                    f"Error updating the total disbursed amount and the current balance, please retry again later, "
                    f"exception: {e.args}"
                )
            )

        return balance_after

    def return_disbursed_amount_for_cancelled_trx(self, amount):
        """
        Update the total disbursement amount and the current balance after each pending -> failed transaction
        :param amount: the pending amount for being disbursed
        :return: True/False
        """
        try:
            current_balance_before = self.current_balance
            self.total_disbursed_amount -= round(Decimal(amount), 2)
            self.current_balance += round(Decimal(amount), 2)
            self.save()
            BUDGET_LOGGER.debug(
                f"[message] [CUSTOM BUDGET UPDATE] [{self.disburser.username}] -- returned amount: {amount}, "
                f"current balance before: {current_balance_before}, current balance after: {self.current_balance}"
            )
        except Exception:
            raise ValueError(
                _(
                    f"Error adding to the current balance and cutting from the total disbursed amount"
                )
            )

        return self.current_balance

    def get_current_balance(self):
        with transaction.atomic():
            print("===============GETTING BALACE=================")
            budget_obj = Budget.objects.select_for_update().get(id=self.id)
            return budget_obj.current_balance


class FeeSetup(models.Model):
    """
    Model for applying and calculating fees based on issuer type for every entity with custom budget
    """

    VODAFONE = "vf"
    ETISALAT = "es"
    ORANGE = "og"
    AMAN = "am"
    BANK_CARD = "bc"
    BANK_WALLET = "bw"

    ISSUER_CHOICES = [
        (VODAFONE, _("Vodafone")),
        (ETISALAT, _("Etisalat")),
        (ORANGE, _("Orange")),
        (AMAN, _("Aman")),
        (BANK_CARD, _("Bank Card")),
        (BANK_WALLET, _("Bank Wallet")),
    ]

    FIXED_FEE = "f"
    PERCENTAGE_FEE = "p"
    MIXED_FEE = "m"

    FEE_CHOICES = [
        (FIXED_FEE, _("Fixed Fee")),
        (PERCENTAGE_FEE, _("Percentage Fee")),
        (MIXED_FEE, _("Mixed Fee")),
    ]

    budget_related = models.ForeignKey(
        Budget, on_delete=models.CASCADE, related_name="fees", verbose_name=_("Budget")
    )
    issuer = models.CharField(
        _("Issuer type"), max_length=2, choices=ISSUER_CHOICES, null=False, blank=False
    )
    fee_type = models.CharField(
        _("Fee type"), max_length=1, choices=FEE_CHOICES, null=False, blank=False
    )
    fixed_value = models.DecimalField(
        _("Fixed value"),
        validators=[
            MinValueValidator(round(Decimal(0.0), 0)),
            MaxValueValidator(round(Decimal(100.0), 1)),
        ],
        max_digits=5,
        decimal_places=2,
        default=0,
        null=True,
        blank=True,
        help_text=_("Applied with transactions of type fixed or mixed fees"),
    )
    percentage_value = models.DecimalField(
        _("Percentage value"),
        validators=[
            MinValueValidator(round(Decimal(0.0))),
            MaxValueValidator(round(Decimal(100.0), 1)),
        ],
        max_digits=5,
        decimal_places=2,
        default=0,
        null=True,
        blank=True,
        help_text=_("Applied with transactions of type percentage or mixed fees"),
    )
    min_value = models.DecimalField(
        _("Minimum value"),
        validators=[
            MinValueValidator(round(Decimal(0.0), 0)),
            MaxValueValidator(round(Decimal(100.0), 1)),
        ],
        max_digits=5,
        decimal_places=2,
        default=0,
        null=True,
        blank=True,
        help_text=_(
            "Fees value to be added instead of the fixed/percentage fees when "
            "the total calculated fees before 14% is less than this min value"
        ),
    )
    max_value = models.DecimalField(
        _("Maximum value"),
        validators=[
            MinValueValidator(round(Decimal(0.0), 0)),
            MaxValueValidator(round(Decimal(10000.0), 1)),
        ],
        max_digits=5,
        decimal_places=2,
        default=0,
        null=True,
        blank=True,
        help_text=_(
            "Fees value to be added instead of the fixed/percentage fees when "
            "the total calculated fees before 14% is greater than this max value"
        ),
    )

    @property
    def issuer_choice_verbose(self):
        """Return the corresponding verbose name of the used issuer type"""
        return dict(FeeSetup.ISSUER_CHOICES)[self.issuer]

    @property
    def fee_type_choice_verbose(self):
        """Return the corresponding verbose name of the used fees type"""
        return dict(FeeSetup.FEE_CHOICES)[self.fee_type]

    class Meta:
        verbose_name = "Fee Setup"
        verbose_name_plural = "Fees Setups"
        unique_together = ["budget_related", "issuer"]
        get_latest_by = "-id"
        ordering = ["-id"]

    def __str__(self):
        """String representation for a fee setup object"""
        return f"{self.fee_type_choice_verbose} setup for {self.issuer_choice_verbose}"


class TopupRequest(AbstractTimeStamp):

    client = models.ForeignKey(
        "users.RootUser",
        on_delete=models.CASCADE,
        related_name="topup_request",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(
        max_length=20,
        choices=[
                ('egyptian_pound', _('Egyptian Pound (L.E)')),
                ('american_dollar', _('American Dollar ($)'))
            ],
        default="egyptian_pound"
    )
    transfer_type = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    username = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    from_bank = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    to_bank = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    from_account_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    to_account_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    from_account_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    to_account_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    from_date = models.DateField(
        blank=True,
        null=True
    )
    to_attach_proof = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )
    automatic = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Topup Request"
        verbose_name_plural = "Topup Requests"
        ordering = ["-id"]


class TopupAction(AbstractTimeStamp):

    client = models.ForeignKey(
        "users.RootUser",
        on_delete=models.CASCADE,
        related_name="topup_action",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    fx_ratio_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    balance_before = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, null=True, blank=True
    )

    balance_after = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, null=True, blank=True
    )

    notes = models.CharField(max_length=500, blank=True, null=True)

    automatic = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Topup Action"
        verbose_name_plural = "Topup Actions"
        ordering = ["-id"]


class ExcelFile(AbstractTimeStamp):
    """
    Model for store Excel files with their users
    """

    file_name = models.CharField(max_length=100, null=False, blank=False, default="")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="my_excel_files",
        verbose_name=_("Owner"),
    )


class VodafoneBalance(AbstractTimeStamp):

    balance = models.CharField(max_length=100, null=False, blank=False)
    super_agent = models.CharField(max_length=100, null=False, blank=False)

    class Meta:
        verbose_name = "Vodafone Balance"
        verbose_name_plural = "Vodafone Monthly Balances"
        ordering = ["-id"]


class VodafoneDailyBalance(VodafoneBalance):
    class Meta:
        verbose_name = "Vodafone Daily Balance"
        verbose_name_plural = "Vodafone Daily Balances"
        ordering = ["-id"]


class ClientIpAddress(AbstractTimeStamp):
    client = models.ForeignKey(
        "users.RootUser",
        on_delete=models.CASCADE,
        related_name="ip_address",
    )
    ip_address = models.CharField(max_length=100, null=False, blank=False)
    
    class Meta:
        verbose_name = "Client IP Address"
        verbose_name_plural = "Client IP Addresses"
        ordering = ["-id"]
