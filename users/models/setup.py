from django.db import models
from django.utils.functional import cached_property


class Setup(models.Model):
    """
    Setup model to save the state of the entity root setup
    """
    # root user
    user = models.OneToOneField('users.User', on_delete=models.CASCADE)
    levels_setup = models.BooleanField(default=False)
    users_setup = models.BooleanField(default=False)
    category_setup = models.BooleanField(default=False)
    format_setup = models.BooleanField(default=False)
    collection_data_setup = models.BooleanField(default=False)

    def __str__(self):
        return '{0}_setup'.format(str(self.user))

    def can_pass(self):
        if all([self.levels_setup, self.users_setup, self.category_setup, self.format_setup]):
            if self.user.has_perm('users.has_collection'):
                return self.collection_data_setup
            return True
        return False

    def can_add_users(self):
        if self.levels_setup:
            return True
        return False

    @cached_property
    def percentage(self):
        per = 0
        if self.user.has_perm('users.has_collection'):
            if self.levels_setup:
                per += 20
                if self.users_setup:
                    per += 20
                    if self.category_setup:
                        per += 20
                        if self.format_setup:
                            per += 20
                            if self.collection_data_setup:
                                per += 20
        # users.has_disbursement
        else:
            if self.levels_setup:
                per += 25
                if self.users_setup:
                    per += 25
                    if self.category_setup:
                        per += 25
                        if self.format_setup:
                            per += 25
        return per
