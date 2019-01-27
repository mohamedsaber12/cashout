from __future__ import unicode_literals

from datetime import timedelta
from django.utils.timezone import datetime, now
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import Q
from django.http import JsonResponse
from django.conf import settings

# Create your models here.
from django_extensions.db.models import TimeStampedModel

from data.utils import update_user_last_seen


class FileDataManager(models.Manager):

    def search_file_data(self, file_obj, value, from_datetime=None, to_datetime=None):
        result = Q()
        if from_datetime:
            result &= Q(created_at__gte=from_datetime)
        if to_datetime:
            result &= Q(created_at__lte=to_datetime)
        compound_statement = (Q(phone_no=value) | Q(
            payment_status=value) | Q(transaction_id=value))
        return super(FileDataManager, self).get_queryset().filter(
            Q(doc=file_obj) &
            compound_statement &
            result
        ).order_by('-created_at')

    def transactions_in_range(self, user, start_date=None, end_date=None):
        """
        Returns client data that had happened in specific range of time.
        Start_date can be empty to fetch the very first transactions.
        End_data can be empty, it'll be assigned to today.
        :param user: Transaction's user object who sends the request.
        :param start_date: Date which indicates the beginning of filtration.
        :param end_date: Date which indicates the end of filtration.
        :return: QuerySet
        """
        query = self.get_queryset()

        # Inserting default values if no specific dates were provided.
        if not end_date:
            end_date = datetime.now()
        if not start_date or (end_date-start_date).days > 45:
            start_date = end_date - timedelta(days=45)

        client_data = query.filter(
            file_category__user_created=user.parent,
            transactions__datetime__date__range=(start_date, end_date),
            has_transaction=True
        )

        # Append all dates between start and end dates to user's seen days.
        if client_data:
            for date in [start_date + timedelta(days=x) for x in range((end_date-start_date).days + 1)]:
                update_user_last_seen(user, end_date=date)

        return client_data

    def unseen_transactions(self, user):
        """
        Returns all unseen transactions happened in last 45 days.
        :param user: Transaction's user object who sends the request.
        :return: QuerySet
        """
        query = self.get_queryset()
        # User's seen days
        try:
            days = user.transactions_seen_days or []
        except AttributeError:
            days = []

        clients_data = query.filter(
            Q(file_category__user_created=user),
            Q(has_transaction=True) |
            Q(has_partial_transaction=True)
        )
        today_clients_data = clients_data.filter(
            transactions__datetime__day=now().date().day,
            transactions__datetime__month=now().date().month,
            transactions__is_seen=False,
        )
        if days:
            clients_data = clients_data.exclude(
                date__in=days,
            )
        return (clients_data | today_clients_data).distinct()

    def transaction_in_doc(self, _doc):
        """
        Returns all records belongs to specific doc.
        :param _doc: Uploaded document that transactions will be filtered against.
        :return: QuerySet
        """
        query = self.get_queryset()
        try:
            transactions = query.filter(
                doc=_doc,
                has_transaction=True
            )
        except:
            # Query-related error.
            transactions = []

        return transactions


class FileData(TimeStampedModel):
    doc = models.ForeignKey('data.Doc', null=True, related_name='filedata', on_delete=models.CASCADE)
    data = JSONField(null=True, blank=True, default=dict, db_index=True)
    date = models.DateField(blank=True, null=True)
    is_draft = models.BooleanField(default=0, verbose_name='Drafted')
    is_downloaded = models.BooleanField(default=0)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.CASCADE, related_name='file_data')
    has_full_payment = models.BooleanField(default=False)
    objects = FileDataManager()

    class Meta:
        verbose_name_plural = 'File Data'
        get_latest_by = 'date'

    def __unicode__(self):
        return "Data"

    def __str__(self):
        return "Data"

    def doc_name(self):
        try:
            return self.doc.filename()
        except AttributeError:
            return self.__str__()
