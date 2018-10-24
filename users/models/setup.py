from django.db import models


class Setup(models.Model):
    user = models.OneToOneField('users.User', on_delete=models.CASCADE)
    levels_setup = models.BooleanField(default=False)
    users_setup = models.BooleanField(default=False)

    def __str__(self):
        return '{0}_setup'.format(str(self.user))

    def can_pass(self):
        if all([self.levels_setup, self.users_setup]):
            return True
        return False

    def can_add_users(self):
        if self.levels_setup:
            return True
        return False
