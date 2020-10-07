import os
import random, string, datetime, logging
import xlsxwriter
from urllib.parse import urlencode

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.core.paginator import PageNotAnInteger, EmptyPage
from django.core.paginator import Paginator
from django.utils.timezone import now
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.contrib.auth.base_user import BaseUserManager
from django.shortcuts import redirect
from django.urls import reverse_lazy

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
    remote_addr = request.META.get('REMOTE_ADDR')

    if remote_addr:
        return remote_addr
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]

    return None


def update_filename(instance, filename):
    """
    update document name
    :param instance: doc instance
    :param filename: filename of uploaded file
    :return:
    """
    now = datetime.datetime.now()
    path = "documents/files_uploaded/%d/%s/" %(now.year, now.month)
    file, ext = filename.split('.')
    filename = file + '_' + instance.owner.username + '_' +\
               ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(9)) + \
               '.' + ext
    return os.path.join(path, filename)


def generate_pass():
    return BaseUserManager().make_random_password(length=6)


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
        DOWNLOAD_LOGGER.debug(
                f"[message] [DOWNLOAD VALIDATION ERROR] [{user}] -- cannot be saved with new transaction seen dates"
        )
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
            name=category.name,
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
            category=category,
            hierarchy=category.user_created.hierarchy
        )


def excell_letter_to_index(col_name):
    """convert excell column name(string) ex: 'A' or 'AB' to its numeric position"""
    num = 0
    for c in col_name:
        if c in string.ascii_letters:
            num = num * 26 + (ord(c.upper()) - ord('A')) + 1
    return num


def excell_position(col_index,row_index):
    """
    @param col_index int: excel column index (zero indexed).
    @param row_index int: excel row index (zero indexed).
    return string: corresponding column row position, ex: 'A1'.
    """
    return xlsxwriter.utility.xl_col_to_name(col_index) + str(row_index+1)


def export_excel(file_path, data):
    # Create a workbook and add a worksheet.
    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet()

    # Iterate over the data and write it out row by row.
    for row, items in enumerate(data):
        for col, item in enumerate(items):
            worksheet.write(row, col, item)

    workbook.close()


def randomword(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))


def deliver_mail(user_obj, subject_tail, message_body, recipients=None):
    """
    Send a message to inform the user with disbursement/collection related action.
    :param user_obj: Request's user instance that the mail will be sent to.
    :param subject_tail: Tailed mail subject header after his/her chosen mail header brand.
    :param message_body: Body of the message that will be sent.
    :param recipients: If there are multiple makers/checkers to be notified.
    :return: Action of sending the mail to the user.
    """
    from_email = settings.SERVER_EMAIL
    if recipients is None:
        subject = f'[{user_obj.brand.mail_subject}]' + subject_tail
        recipient_list = [user_obj.email]
    else:
        subject = f'[{recipients[0].brand.mail_subject}]' + subject_tail
        recipient_list = [recipient.email for recipient in recipients]
        for mail in recipient_list:
            mail_to_be_sent = EmailMultiAlternatives(subject, message_body, from_email, [mail])
            mail_to_be_sent.attach_alternative(message_body, "text/html")
            mail_to_be_sent.send()
        return
    mail_to_be_sent = EmailMultiAlternatives(subject, message_body, from_email, recipient_list)
    mail_to_be_sent.attach_alternative(message_body, "text/html")
    return mail_to_be_sent.send()
