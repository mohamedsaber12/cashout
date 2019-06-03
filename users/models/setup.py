from django.db import models
from django.utils.functional import cached_property


class Setup(models.Model):
    """
    Setup model to save the state of the entity root setup
    """
    # root user
    user = models.OneToOneField('users.User', on_delete=models.CASCADE)
    #disbursement
    pin_setup = models.BooleanField(default=False)
    levels_setup = models.BooleanField(default=False)
    maker_setup = models.BooleanField(default=False)
    checker_setup = models.BooleanField(default=False)
    category_setup = models.BooleanField(default=False)
    #collection
    uploaders_setup = models.BooleanField(default=False)
    format_collection_setup = models.BooleanField(default=False)
    collection_setup = models.BooleanField(default=False)

    def __str__(self):
        return '{0}_setup'.format(str(self.user))

    def can_pass_disbursement(self):
        return all([self.levels_setup, self.maker_setup,self.checker_setup, self.category_setup,
                    self.pin_setup])
        
    def can_pass_collection(self):
        return all([self.collection_setup, self.format_collection_setup, 
                    self.uploaders_setup])

    def can_add_users(self):
        if self.levels_setup:
            return True
        return False

    @cached_property
    def disbursement_percentage(self):
        per = 0
        if self.pin_setup:
            per += 20
            if self.maker_setup:
                per += 20
                if self.category_setup:
                    per += 20
                    if self.levels_setup:
                        per += 20
                        if self.checker_setup:
                            per += 20
        return per

    @cached_property
    def collection_percentage(self):
        per = 0
        if self.collection_setup:
            per += 40
            if self.format_collection_setup:
                per += 30
                if self.uploaders_setup:
                    per += 30          
        return per


    def disbursement_enabled_steps(self):
        """1-indexed"""
        steps = []
        if self.pin_setup == True:
            steps.append('1')
        if self.maker_setup == True:
            steps.append('2')
        if self.levels_setup == True:
            steps.append('3')
        if self.checker_setup == True:
            steps.append('4')
        if self.category_setup == True:
            steps.append('5')
        return steps

    def collection_enabled_steps(self):
        """1-indexed"""
        steps = []
        if self.uploaders_setup == True:
            steps.append('1')
        if self.format_collection_setup == True:
            steps.append('2')
        if self.collection_setup == True:
            steps.append('3')
      
        return steps
