from __future__ import unicode_literals
import operator
from datetime import datetime
from functools import reduce
from django.db import models
from django.conf import settings
from users.models import RootUser

# Create your models here.
from data.models import FileData


class TransactionManager(models.Manager):

    def search_transactions(self, search_value):
        """
        Returns all transactions related to someuser.
        :param search_value: String query holds user's name.
        :return: QuerySet
        """
        return super(TransactionManager, self).get_queryset().filter(to_user=search_value)


class Transactions(models.Model):
    SUCCESS = 1
    FAILURE = 0
    STATUS = [
        (FAILURE, 'Failure'),
        (SUCCESS, 'Success'),
    ]
    TYPES = [
        (0, 'Full payment'),
        (1, 'Partial Payment'),
        (2, 'Over Payment'),
    ]

    biller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)
    file_data = models.ForeignKey(FileData, null=True, related_name='transactions', on_delete=models.DO_NOTHING)
    rrn = models.CharField(
        max_length=16,
        verbose_name='Transaction Ref for the aggregator',
        unique=True, primary_key=True
    )
    amount = models.FloatField(verbose_name='Paid Amount of Installment')
    fine = models.FloatField(verbose_name='Paid Fines of Installment', blank=True, null=True, default=0)
    datetime = models.DateTimeField(auto_now_add=True, verbose_name='Time of transaction')
    status = models.SmallIntegerField(choices=STATUS, verbose_name='Status', default=1)
    type_of_payment = models.SmallIntegerField(choices=TYPES, default=0, verbose_name='Type of payment')
    is_seen = models.BooleanField(default=False)
    objects = TransactionManager()

    class Meta:
        verbose_name_plural = 'Transactions'
        get_latest_by = 'datetime'
        ordering = ['datetime']

    # Methods
    def __str__(self):
        return self.rrn
