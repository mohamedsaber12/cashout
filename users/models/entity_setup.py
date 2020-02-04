from django.db import models
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from rest_framework_expiring_authtoken.models import ExpiringToken
from django.db.models import Q


class EntitySetupManager(models.Manager):
    def uncomplete_entity_creations(self):
        return self.get_queryset().filter(
            Q(agents_setup=False)|
            Q(fees_setup=False)
        )


class EntitySetup(models.Model):
    """
    Entity Setup model to save the state of the entity creation setup by super admin
    """
    #superadmin
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='entity_setups')
    #root
    entity = models.OneToOneField('users.User', on_delete=models.CASCADE)
    agents_setup = models.BooleanField(default=False)
    fees_setup = models.BooleanField(default=False)

    objects = EntitySetupManager()

    def __str__(self):
        return '{0}_setup'.format(str(self.user))

    def can_pass(self):
        return all([self.agents_setup, self.fees_setup])

    @cached_property
    def percentage(self):
        per = 30
        if self.agents_setup:
            per += 30
            if self.fees_setup:
                per += 40
        return per

    def get_reverse(self):
        if not self.agents_setup:
            token, created = ExpiringToken.objects.get_or_create(user=self.entity)
            if created:
                return reverse_lazy('disbursement:add_agents', kwargs={'token': token.key})
            if token.expired():
                token.delete()
                token = ExpiringToken.objects.create(user=self.entity)
            return reverse_lazy('disbursement:add_agents', kwargs={'token': token.key})

        if not self.fees_setup:
            token, created = ExpiringToken.objects.get_or_create(user=self.entity)
            if created:
                return reverse_lazy('users:add_fees', kwargs={'token': token.key})
            if token.expired():
                token.delete()
                token = ExpiringToken.objects.create(user=self.entity)
            return reverse_lazy('users:add_fees', kwargs={'token': token.key})    

