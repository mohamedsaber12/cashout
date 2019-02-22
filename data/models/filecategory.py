from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.


class FileCategoryManager(models.Manager):

    def get_by_hierarchy(self, hierarchy):
        return self.get_queryset().filter(user_created__hierarchy=hierarchy)


class FileCategory(models.Model):

    MIN_IDS_LENGTH = 2

    name = models.CharField(
        max_length=128, unique=False, verbose_name=_('Description'))
    user_created = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.CASCADE, 
        related_name='file_category')
    unique_field = models.CharField(max_length=128,
                                    verbose_name=_('msisdn header position'))
    amount_field = models.CharField(max_length=128,
                                    verbose_name=_('amount header position'),
                                    help_text=_('for ex: loan_field'))
    no_of_reviews_required = models.PositiveSmallIntegerField(default=3,
                                                              verbose_name=_('Number of reviews'),
                                                              help_text=_('Number of reviews required to be disbursed')
                                                              )
    

    objects = FileCategoryManager()

    class Meta:
        verbose_name_plural = 'File Categories'
        unique_together = (('user_created', 'name'),)

    def __unicode__(self):
        return self.user_created.username

    def __str__(self):
        return self.user_created.username


    def get_field_position(self,field):
        letter, row = field.split('-')
        return letter, int(row)

    def starting_row(self):
        """
        return zero indexed row position.
        starting_row = header row number + 1 row (first row of data) - 1 row for zero indexing
        """
        return self.get_field_position(self.unique_field)[1]

    def fields_cols(self):
        """return tuple of zero indexed columns positions."""
        from data.utils import excell_letter_to_index

        return (
            excell_letter_to_index(
                self.get_field_position(self.amount_field)[0]
            ) -1 ,
            excell_letter_to_index(
                self.get_field_position(self.unique_field)[0]
            ) - 1,
        )
        
