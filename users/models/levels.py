from django.db import models

LEVELS = (
    (1, 'Level 1'),
    (2, 'Level 2'),
    (3, 'Level 3'),
    (4, 'Level 4'),
)


class Levels(models.Model):
    max_amount_can_be_disbursed = models.FloatField(default=0)
    level_of_authority = models.PositiveSmallIntegerField(choices=LEVELS)
    user = models.ForeignKey('users.User', related_name='levels', on_delete=models.CASCADE)

    def __str__(self):
        return f'amount is {self.max_amount_can_be_disbursed} of level {self.level_of_authority}'