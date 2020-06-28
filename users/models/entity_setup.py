from django.db import models
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from rest_framework_expiring_authtoken.models import ExpiringToken


class EntitySetupManager(models.Manager):
    """
    Manager for the EntitySetup model
    """

    def uncomplete_entity_creations(self):
        """Check if any entity_setup object has any uncompleted setup of agents or fees"""
        return self.get_queryset().filter(
            Q(agents_setup=False) | Q(fees_setup=False)
        )


class EntitySetup(models.Model):
    """
    Entity Setup model to save the state of the entity creation setup by super admin
    """
    agents_setup = models.BooleanField(default=False, verbose_name=_("Is agent setup completed for the entity?"))
    fees_setup = models.BooleanField(default=False, verbose_name=_("Is fees setup completed for the entity?"))
    is_normal_flow = models.BooleanField(default=True, verbose_name=_("Is the regular Vodafone flow setup/disb?"))
    entity = models.OneToOneField(
            'users.RootUser',
            on_delete=models.CASCADE,
            related_name='root_entity_setups',
            help_text=_("Root user, the admin of the entity")
    )
    user = models.ForeignKey(
            'users.SuperAdminUser',
            on_delete=models.CASCADE,
            related_name='entity_setups',
            verbose_name=_("SuperAdmin"),
            help_text=_("The owner who on-board entities. ex: PayMob")
    )

    objects = EntitySetupManager()

    def __str__(self):
        """:return: String representation of each entity setup object"""
        return f'{self.user} setup for {self.entity} entity'

    def can_pass(self):
        """
        Check if entity setup -agents and fees- is completed
        :return True/False
        """
        return all([self.agents_setup, self.fees_setup])

    @cached_property
    def percentage(self):
        """
        agents_setups represents 30% of the whole setup process
        fees_setup    represents 40% of the whole setups process
        :return: % of completed setups
        """
        per = 30
        if self.agents_setup:
            per += 30
            if self.fees_setup:
                per += 40
        return per

    def get_reverse(self):
        """Redirect SuperAdmin to complete setup of a certain step if not completed"""
        if not self.agents_setup:
            token, created = ExpiringToken.objects.get_or_create(user=self.entity)
            if token.expired():
                token.delete()
                token = ExpiringToken.objects.create(user=self.entity)
            return reverse_lazy('disbursement:add_agents', kwargs={'token': token.key})

        if not self.fees_setup:
            token, created = ExpiringToken.objects.get_or_create(user=self.entity)
            if token.expired():
                token.delete()
                token = ExpiringToken.objects.create(user=self.entity)
            return reverse_lazy('users:add_fees', kwargs={'token': token.key})
