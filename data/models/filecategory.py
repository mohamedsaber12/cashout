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
    identifier1 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name='Header 1')
    identifier2 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name='Header 2')
    identifier3 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name='Header 3')
    identifier4 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name='Header 4')
    identifier5 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name='Header 5')
    identifier6 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name='Header 6')
    identifier7 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name='Header 7')
    identifier8 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name='Header 8')
    identifier9 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name='Header 9')
    identifier10 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name='Header 10')
    num_of_identifiers = models.IntegerField(default=0, verbose_name='Number of identifiers filled')

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
