from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.


class FileCategoryManager(models.Manager):

    def get_by_hierarchy(self, hierarchy):
        return self.get_queryset().filter(user_created__hierarchy=hierarchy).first()


class FileCategory(models.Model):
    name = models.CharField(
        max_length=128, unique=False, verbose_name=_('File Category Name'))
    user_created = models.OneToOneField(
        settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.CASCADE, related_name='file_category')
    unique_field = models.CharField(max_length=128, null=True, blank=True,
                                    verbose_name=_('What is the unique field?'))
    amount_field = models.CharField(max_length=128, null=True, blank=True,
                                    verbose_name=_('what is amount field?'),
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
        return self.user_created.username + ' ' + self.name

    def __str__(self):
        return self.user_created.username + ' ' + self.name
