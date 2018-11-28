from django.db import models
from django.utils.functional import cached_property


class Setup(models.Model):
    """
    Setup model to save the state of the entity root setup
    """
    user = models.OneToOneField('users.User', on_delete=models.CASCADE)
    levels_setup = models.BooleanField(default=False)
    users_setup = models.BooleanField(default=False)
    category_setup = models.BooleanField(default=False)

    def __str__(self):
        return '{0}_setup'.format(str(self.user))

    def can_pass(self):
        if all([self.levels_setup, self.users_setup, self.category_setup]):
            return True
        return False

    def can_add_users(self):
        if self.levels_setup:
            return True
        return False

    @cached_property
    def percentage(self):
        per = 0
        if self.levels_setup:
            per += 30
            if self.users_setup:
                per += 40
                if self.category_setup:
                    per += 30
        return per
