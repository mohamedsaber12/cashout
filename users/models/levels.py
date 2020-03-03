from django.db import models
from django.utils.translation import gettext_lazy as _


LEVELS = (
    (1, 'Level 1'),
    (2, 'Level 2'),
    (3, 'Level 3'),
    (4, 'Level 4'),
)


class Levels(models.Model):
    """
    Model reference for levels of authority of users in the hierarchy tree
    Added by the root of the tree only
    """
    max_amount_can_be_disbursed = models.FloatField(default=0, verbose_name=_('Max amount can be disbursed'))
    level_of_authority = models.PositiveSmallIntegerField(choices=LEVELS, null=True, blank=True)
    created = models.ForeignKey(
            'users.User',
            on_delete=models.CASCADE,
            null=True,
            help_text=_('Root user who created the levels, and have the ability to modify their values.')
    )

    class Meta:
        ordering = ('max_amount_can_be_disbursed', )

    def __str__(self):
        return f'Amount is {self.max_amount_can_be_disbursed} of level {self.level_of_authority}'

    @classmethod
    def update_levels_authority(cls, root):
        """
        order levels in ascending order by max_amount_can_be_disbursed and 
        give them a level number(level_of_authority).
        """
        levels_qs = cls.objects.filter(created=root)
        levels_values = list(levels_qs.values_list('max_amount_can_be_disbursed', flat=True))

        for level in levels_qs:
            level.level_of_authority = levels_values.index(level.max_amount_can_be_disbursed) + 1
            level.save()    
