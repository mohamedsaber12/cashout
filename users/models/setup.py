from django.db import models


class Setup(models.Model):
    user = models.OneToOneField('users.User', on_delete=models.CASCADE)
    levels_setup = models.BooleanField(default=False)
    users_setup = models.BooleanField(default=False)

    def can_pass(self):
        if all([self.levels_setup, self.users_setup]):
            return True
        return False
