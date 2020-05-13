# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import gettext_lazy as _


class FileCategoryManager(models.Manager):
    """
    Manager for the FileCategory model
    """
    def get_by_hierarchy(self, hierarchy):
        """
        :param hierarchy: user hierarchy
        :return: Get all file categories related to/created by specific hierarchy family of users
        """
        return self.get_queryset().filter(user_created__hierarchy=hierarchy)


class FileCategory(models.Model):
    """
    Model for defining the format of the uploaded file for disbursement documents
    """
    MIN_IDS_LENGTH = 2

    name = models.CharField(max_length=128, unique=False, verbose_name=_('Description'))
    user_created = models.ForeignKey(
            'users.RootUser',
            on_delete=models.CASCADE,
            blank=True,
            null=True,
            related_name='file_category'
    )
    unique_field = models.CharField(max_length=128, verbose_name=_('mobile number header position'))
    amount_field = models.CharField(
            max_length=128,
            verbose_name=_('amount header position'),
            help_text=_('For ex: loan_field')
    )
    issuer_field = models.CharField(
            max_length=128,
            blank=True,
            null=True,
            verbose_name=_('issuer option header position'),
            help_text=_('Only activated at sheets with multiple issuers')
    )
    no_of_reviews_required = models.PositiveSmallIntegerField(
            default=3,
            verbose_name=_('number of reviews'),
            help_text=_('Number of reviews required for a doc with this file category to be disbursed')
    )
    
    objects = FileCategoryManager()

    class Meta:
        verbose_name_plural = 'File Categories'
        unique_together = ['user_created', 'name']

    def __str__(self):
        """String representation for FileCategory model objects"""
        return f"Format: {self.name} of user: {self.user_created.username}"

    def get_field_position(self, field):
        """
        :param field: ex: A-1 or B-1
        :return: tuple of (str(letter), int(row)) ex: ('A', 1)
        """
        letter, row = field.split('-')
        return letter, int(row)

    def starting_row(self):
        """
        Define index of the row -at excel sheet- on which validation process will be ran
        starting_row = header row number + 1 row (first row of data) - 1 row for zero indexing
        :return: zero indexed row position
        """
        return self.get_field_position(self.unique_field)[1]

    def fields_cols(self):
        """
        :return: tuple of zero indexed columns positions (amount_excel_column_position, msisdn_excel_column_position)
        """
        # Imported here because of a circular import issue
        from ..utils import excell_letter_to_index

        return (
            excell_letter_to_index(self.get_field_position(self.amount_field)[0]) - 1 ,
            excell_letter_to_index(self.get_field_position(self.unique_field)[0]) - 1
        )
