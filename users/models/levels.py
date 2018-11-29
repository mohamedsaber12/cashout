from django.db import models

LEVELS = (
    (1, 'Level 1'),
    (2, 'Level 2'),
    (3, 'Level 3'),
    (4, 'Level 4'),
)


class Levels(models.Model):
    """
    Model reference for levels of authority
    of users in the hierarchy tree
    Added by the root of the tree only
    """
    max_amount_can_be_disbursed = models.FloatField(default=0)
    level_of_authority = models.PositiveSmallIntegerField(
        choices=LEVELS, null=True, blank=True)
    created = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f'amount is {self.max_amount_can_be_disbursed} of level'

    class Meta:
        ordering = ('-max_amount_can_be_disbursed',)
