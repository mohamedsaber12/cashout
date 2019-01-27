import os
import random, string, datetime, urllib, logging
from urllib.parse import urlencode

from django.core.paginator import PageNotAnInteger, EmptyPage
from django.core.paginator import Paginator
from django.utils.timezone import now
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.contrib.auth.base_user import BaseUserManager
from django.shortcuts import redirect
from django.urls import reverse_lazy
from two_factor.views import SetupView as BaseSetupView

from data.models.filecategory import FileCategory
from data.models.category_data import Format

DOWNLOAD_LOGGER = logging.getLogger("download_serve")


def validate_file_extension(value):
    if not value.name.endswith('xlxs'):
        raise ValidationError(u'Error message')


def get_client_ip(request):
    """
    to get client ip request
    :param request:
    :return:
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def update_filename(instance, filename):
    """
    update document name
    :param instance: doc instance
    :param filename: filename of uploaded file
    :return:
    """
    now = datetime.datetime.now()
    path = "documents/%d/%s/" %(now.year, now.month)
    file, ext = filename.split('.')
    filename = file + '_' + instance.owner.username + '_' +\
               ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(9)) + \
               '.' + ext
    return os.path.join(path, filename)


def generate_pass():
    return BaseUserManager().make_random_password(length=6)


class SetupView(BaseSetupView):
    """
    Disbursement checking
    """
    def get(self, request, *args, **kwargs):
        """
        Start the setup wizard. Redirect if already enabled.
        """
        if request.user.can_disburse:
            return super(SetupView, self).get(request, *args, **kwargs)
        else:
            return redirect(reverse_lazy('data:main_view'))


def redirect_params(url, kw, params=None):
    response = reverse_lazy(url, kwargs=kw)
    if params:
        query_string = urlencode(params)
    else:
        query_string = ''

    return redirect(response + '?' +query_string)


def pkgen():
    """
    Function to generate reference hash
    ref: https://code-examples.net/en/q/395b9e # python 2 version
    :return:
    """
    from base64 import b32encode
    from hashlib import sha1
    from random import random
    rude = (b'lol',)
    bad_pk = True
    while bad_pk:
        sha1_obj = sha1()
        sha1_obj.update(str(random()).encode('utf-8'))
        pk = b32encode(sha1_obj.hexdigest().encode()).lower()
        bad_pk = False
        for rw in rude:
            if pk.find(rw) >= 0:
                bad_pk = True
        return pk.decode()[:32]


def update_user_last_seen(user, end_date=None, clients_data=None):
    """
    Updates the request's user last seen date and Transaction.is_seen.
    :param user: Request's users instance that'll be updated.
    :param end_date: Datetime that is overriden by now if not provided.
    :param clients_data: A QuerySet of FileData that user's seen.
    :return: Void
    """

    # Append all possible dates to dates[]
    dates = []

    if not end_date:
        end_date = now().date()
    dates.append(end_date)

    if clients_data:
        for file_data in clients_data:
            dates.append(file_data.date)
            try:
                for transaction in file_data.transactions.all():
                    transaction.is_seen = True
                    transaction.save()
            except ObjectDoesNotExist:
                continue

    # Alter user's seen days with non-repeated, less-than-45 dates.
    try:
        dates = list(set(user.transactions_seen_days + dates))
        if len(dates) > 45:
            dates = dates[-45:]
        user.transactions_seen_days = dates
        user.save()
    except ValidationError:
        # Can't save user
        DOWNLOAD_LOGGER.debug('User: {0} cannot be saved with new transaction seen dates.')
    return


def paginator(request, object):
    """
    Function that paginates the object given in the parameter
    """
    paginator_obj = Paginator(object, 100)
    page = request.GET.get('page')
    try:
        docs = paginator_obj.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        docs = paginator_obj.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        docs = paginator_obj.page(paginator_obj.num_pages)
    return docs

def combine_data():
    categories = FileCategory.objects.all()
    for category in categories:
        Format.objects.create(
            identifier1=category.identifier1,
            identifier2=category.identifier2,
            identifier3=category.identifier3,
            identifier4=category.identifier4,
            identifier5=category.identifier5,
            identifier6=category.identifier6,
            identifier7=category.identifier7,
            identifier8=category.identifier8,
            identifier9=category.identifier9,
            identifier10=category.identifier10,
            category=category
        )