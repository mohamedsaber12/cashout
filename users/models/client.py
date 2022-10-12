from django.core.validators import MaxValueValidator, MinLengthValidator
from django.db import models
from django.shortcuts import reverse
from django.utils.translation import gettext_lazy as _

from ..models import User


class ClientManager(models.Manager):
    """
    Manager for the Client model
    """

    def toggle(self, *args, **kwargs):
        """Toggle client object activation state"""
        try:
            user = self.get(*args, **kwargs)
            user.toggle_activation()
            return True
        except:
            return False


class Client(models.Model):
    """
    Model to track/manage entities/clients per SuperAdmin user
    """

    # Agents onboarding choices
    NEW_SUPERAGENT_AGENTS = 0
    EXISTING_SUPERAGENT_NEW_AGENTS = 1
    EXISTING_SUPERAGENT_AGENTS = 2
    P2M = 3
    AGENTS_ONBOARDING_CHOICES = [
        (NEW_SUPERAGENT_AGENTS, _("New superagent and new agents")),
        (EXISTING_SUPERAGENT_NEW_AGENTS, _("Existing superagent and new agents")),
        (EXISTING_SUPERAGENT_AGENTS, _("Existing superagent and existing agents")),
        (P2M, _("P2M Agent")),
    ]

    is_active = models.BooleanField(default=True)
    fees_percentage = models.PositiveSmallIntegerField(validators=[MaxValueValidator(100)], default=100)
    vodafone_facilitator_identifier = models.CharField(
            _("Vodafone facilitator unique identifier"),
            max_length=150,
            validators=[MinLengthValidator(10)],
            default='',
            null=True,
            blank=True
    )
    custom_profile = models.CharField(
            max_length=50,
            default='',
            null=True,
            blank=True,
            help_text=_("Custom profile name/constant ONLY for clients with custom budgets")
    )
    smsc_sender_name = models.CharField(
            max_length=11,
            default='',
            null=True,
            blank=True,
            help_text=_("SMSC sender name for naming the header of the sms sent at every vf bulk disbursement request")
    )
    agents_onboarding_choice = models.PositiveSmallIntegerField(
            _("Agents Onboarding Choice"),
            db_index=True,
            choices=AGENTS_ONBOARDING_CHOICES,
            default=NEW_SUPERAGENT_AGENTS
    )
    client = models.OneToOneField('users.RootUser', on_delete=models.CASCADE, related_name='client', null=True)
    creator = models.ForeignKey('users.SuperAdminUser', on_delete=models.SET_NULL, related_name='clients', null=True)
    onboarded_by = models.ForeignKey('users.OnboardUser', on_delete=models.SET_NULL, related_name='my_clients', null=True)

    objects = ClientManager()

    class Meta:
        ordering = ['-id']

    def __str__(self):
        """:return: String representation of each client object"""
        return f'The client: {self.client.username} owned by superadmin: {self.creator}'

    def get_absolute_url(self):
        """Success form submit - object saving url"""
        return reverse("users:update_fees", kwargs={'username': self.client.username})

    def toggle_activation(self):
        """Toggle user activation status from active to non-active and vice versa"""
        self.is_active = not self.is_active
        self.save()
        self.client.is_active = not self.is_active
        self.client.save()

    def delete_client(self):
        """Delete all users (makers & checkers) created by specific client whenever deleting it"""
        User.objects.filter(hierarchy=self.client.hierarchy).delete()
        self.delete()

    def get_fees(self):
        """
        Used at the change profile request
        :return: String/Constant that will be used as a value of the NEWPROFILE key
        """
        if self.custom_profile:
            return self.custom_profile
        elif self.fees_percentage == 100:
            return "Full"
        elif self.fees_percentage == 50:
            return "Half"
        else:
            return "No fees"
