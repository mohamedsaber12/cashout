# -*- coding: UTF-8 -*-
from __future__ import print_function

import json
import re
import tablib
import xlrd
import itertools
from dateutil.parser import parse
from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError
from django.utils.translation import gettext as _
from django.urls import reverse

from data.models import Doc
from data.models import FileData
from data.utils import excell_position
from disb.models import DisbursementData
from disb.resources import DisbursementDataResource
from disbursement.settings.celery import app
from users.models import User, MakerUser,CheckerUser
import random
import string

@app.task(ignore_result=False)
def handle_disbursement_file(doc_obj_id):
    """
    A function that parse the document and save it into the File Data
    It has 3 cases :
    Category has files so check if draft or delete stale data
    Category has no files
    """
    doc_obj = Doc.objects.get(id=doc_obj_id)
    
    xl_workbook = xlrd.open_workbook(doc_obj.file.path)
    xl_sheet = xl_workbook.sheet_by_index(0)
    amount_position, msisdn_position = doc_obj.file_category.fields_cols()
    start_index = doc_obj.file_category.starting_row()
    amount, msisdn = [], []
    rows = itertools.islice(xl_sheet.get_rows(), start_index, None)
    for row, cell_obj in enumerate(rows,start_index):
        for pos, item in enumerate(cell_obj):
            if pos == amount_position:
                try:
                    amount.append(float(item.value))
                except ValueError:
                    doc_obj.is_processed = False
                    doc_obj.processing_failure_reason = _(
                        "This file has invalid amount at ") + excell_position(pos,row)
                    doc_obj.save()
                    notify_maker(doc_obj)
                    return False
            elif pos == msisdn_position:
                if item.ctype == 2:
                    str_value = str(int(item.value))
                else:
                    str_value = str(item.value).split('.')[0]
                if str_value.startswith('`'):
                    str_value = str_value.split('`')[-1]
                elif str_value.startswith('1') and len(str_value) == 10:
                    str_value = '0020' + str_value
                elif str_value.startswith('2') and len(str_value) == 12:
                    str_value = '00' + str_value
                elif str_value.startswith('01'):
                    str_value = '002' + str_value
                else:
                    doc_obj.is_processed = False
                    doc_obj.processing_failure_reason = _(
                        "This file has invalid mobile number at ") + excell_position(pos, row)
                    doc_obj.save()
                    notify_maker(doc_obj)
                    return False
                # if msisdn is duplicate    
                if str_value in msisdn:
                    doc_obj.is_processed = False
                    doc_obj.processing_failure_reason = _(
                        "This file has duplicate mobile number at ") + excell_position(pos, row)
                    doc_obj.save()
                    notify_maker(doc_obj)
                    return False
                msisdn.append(str_value)

    amount_length = len(amount)
    if amount_length == len(msisdn):
        data = zip(amount, msisdn)
        try:
            DisbursementData.objects.bulk_create(
                [DisbursementData(doc=doc_obj, amount=float(
                    i[0]), msisdn=i[1]) for i in data]
            )
            doc_obj.total_amount = sum(amount)
            doc_obj.total_count = amount_length
            doc_obj.is_processed = True
            doc_obj.save()
            notify_maker(doc_obj)
            return True
        except IntegrityError:
            doc_obj.is_processed = False
            doc_obj.processing_failure_reason = _("This file contains duplicates")
            doc_obj.save()
            notify_maker(doc_obj)
            return False
    else:
        doc_obj.is_processed = False
        doc_obj.processing_failure_reason = _(
            "This file may has mobile number which has no amount")
        doc_obj.save()
        notify_maker(doc_obj)
        return False


@app.task()
def generate_file(doc_id,user_id):
    """related to disbursement"""
    def randomword(length):
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(length))

    doc_obj = Doc.objects.get(id=doc_id)
    filename = _('failed_disbursed_%s_%s.xlsx') % (str(doc_id), randomword(4))

    dataset = DisbursementDataResource(
        file_category=doc_obj.file_category,
        doc=doc_obj
    )
    dataset = dataset.export()
    file_path = "%s%s%s" % (settings.MEDIA_ROOT,
                            "/documents/disbursement/", filename)
    with open(file_path, "wb") as f:
        f.write(dataset.xlsx)

    user = User.objects.get(id=user_id)
    disb_doc_view_url = settings.BASE_URL + \
        str(reverse('disbursement:disbursed_data', kwargs={'doc_id':doc_id}))

    download_url = settings.BASE_URL + \
        str(reverse('disbursement:download_failed', kwargs={'doc_id': doc_id})) + \
        '?filename=' + filename

    MESSAGE_SUCC = f"""Dear {user.first_name} 
        You can download the failed disbursement data related to this document
        <a href='{disb_doc_view_url}'>{doc_obj.filename()}</a>
        from here <a href="{download_url}" >Download</a>
        Thanks, BR"""
    
    subject = f'[{user.brand.mail_subject}]'

    send_mail(
        from_email=settings.SERVER_EMAIL,
        recipient_list=[user.email],
        subject=subject + _(' Failed Disbursement File Download'),
        message=MESSAGE_SUCC
    )



@app.task(ignore_result=False)
def handle_uploaded_file(doc_obj_id):
    """
    #related to collection#
    A function that parse the document and save it into the File Data
    It has 3 cases :
    Category has files so check if draft or delete stale data
    Category has no files

    :param doc_obj_id: uploaded file id.
    :param category_id: category that contains this file.
    :return: void.
    """
    doc_obj = Doc.objects.get(id=doc_obj_id)
    format = doc_obj.format
    xl_workbook = xlrd.open_workbook(doc_obj.file.path)
    collection_data = doc_obj.collection_data
    # Process excel file row by row.
    xl_sheet = xl_workbook.sheet_by_index(0)
    row_index = 0
    for row in xl_sheet.get_rows():
        if row_index:
            data = tablib.Dataset(headers=format.identifiers())
            excl_data = []
            for cell in row:
                if cell.ctype == 3:  # Date
                    try:
                        cell.value = xlrd.xldate.xldate_as_datetime(cell.value, 0).date().strftime('%d-%m-%Y')
                        excl_data.append(cell.value)

                    except ValueError:
                        excl_data.append(cell.value)

                elif cell.ctype == 2:  # Number
                    val = str(cell.value).split(".")
                    if val[1] == '0':
                        excl_data.append(val[0])
                    else:
                        excl_data.append(str(cell.value))
                else:
                    if re.match(r'\s*(?P<d>\d\d?)(?P<sep>\D)(?P<m>\d\d?)(?P=sep)(?P<Y>\d\d\d\d)', cell.value):
                        cell.value = re.sub('[/.:]', '-', cell.value)

                    elif cell.value.startswith('`'):
                        cell.value = cell.value.split('`')[-1]

                    excl_data.append(str(cell.value))
        else:
            row_index += 1
            continue

        *map(data.append, [excl_data, ]),

        # Specify unique fields to search with.
        processed_data = json.loads(data.json)[0]
        search_dict = {
            'data__%s' % collection_data.unique_field: processed_data[collection_data.unique_field],
            'user__hierarchy': collection_data.user.hierarchy,
            'is_draft': False,
        }
        creation_dict = {
            'user': collection_data.user,
            'is_draft': False,
            'doc': doc_obj,
            'data': processed_data
        }
        # Creates if no records, updates if record with partial exists, skip otherwise.
        file_data = FileData.objects.filter(**search_dict)
        if not file_data:
            file_data = FileData.objects.create(**creation_dict)
        else:
            records_to_be_updated = file_data.filter(has_full_payment=False).first()
            try:
                records_to_be_updated.data = processed_data
                file_data = records_to_be_updated
                records_to_be_updated.save()
            except AttributeError:
                file_data = file_data.first()

        try:
            if collection_data.date_field:
                file_data.date = parse(
                    file_data.data[collection_data.date_field]).date()
            else:
                file_data.date = parse(file_data.data['due_date']).date()
        except (KeyError, ValueError):
            from datetime import datetime
            file_data.date = datetime.now()
        file_data.save()
        
    doc_obj.is_processed = True
    doc_obj.save()
    notify_makers_collection(doc_obj)

@app.task()
def notify_checkers(doc_id, level):
    """related to disbursement"""
    doc_obj = Doc.objects.get(id=doc_id)
    checkers = CheckerUser.objects.filter(
        hierarchy=doc_obj.owner.hierarchy).filter(level__level_of_authority=level)
    if not checkers.exists():
        return

    doc_view_url = settings.BASE_URL + doc_obj.get_absolute_url()
    message = f"""Dear Checker 
        The file named <a href='{doc_view_url}'>{doc_obj.filename()}</a> is ready for disbursement
        Thanks, BR"""
    
    subject = f'[{checkers[0].brand.mail_subject}]'
    
    send_mail(
        from_email=settings.SERVER_EMAIL,
        recipient_list=[checker.email for checker in checkers],
        subject= subject + ' Disbursement Notification',
        message=message
    )


@app.task()
def doc_review_maker_mail(doc_id,review_id):
    """related to disbursement"""
    doc = Doc.objects.get(id=doc_id)
    review = doc.reviews.get(id=review_id)
    maker = doc.owner
    doc_view_url = settings.BASE_URL + doc.get_absolute_url()
    if review.is_ok:
        MESSAGE = f"""Dear {maker.first_name}
            The file named <a href='{doc_view_url}'>{doc.filename()}</a> passed the review 
            number {doc.reviews.filter(is_ok=True).count()} out of {doc.file_category.no_of_reviews_required} by
            the checker: {review.user_created.first_name} {review.user_created.last_name}
            Thanks, BR"""
    else:
        MESSAGE = f"""Dear {maker.first_name}
            The file named <a href='{doc_view_url}'>{doc.filename()}</a> didn't pass the review by
            the checker: {review.user_created.first_name} {review.user_created.last_name}
            and the reason is: {review.comment}
            Thanks, BR"""

    subject = f'[{maker.brand.mail_subject}]'

    send_mail(
        from_email=settings.SERVER_EMAIL,
        recipient_list=[maker.email],
        subject= subject + _(' File Upload Notification'),
        message=MESSAGE
    )

def notify_maker(doc):
    """related to disbursement"""
    maker = doc.owner
    doc_view_url = settings.BASE_URL + doc.get_absolute_url()

    MESSAGE_SUCC = f"""Dear {maker.first_name} 
        The file named <a href='{doc_view_url}'>{doc.filename()}</a> was validated successfully 
        You can now notify checkers, 
        Thanks, BR"""
    MESSAGE_FAIL = f"""Dear {maker.first_name}
        The file named <a href='{doc_view_url}'>{doc.filename()}</a> failed validation
        The reason is: {doc.processing_failure_reason}
        Thanks, BR"""

    message = MESSAGE_SUCC if doc.is_processed else MESSAGE_FAIL
    
    subject = f'[{maker.brand.mail_subject}]'
    
    send_mail(
        from_email=settings.SERVER_EMAIL,
        recipient_list=[maker.email],
        subject= subject + _(' File Upload Notification'),
        message=message
    )


def notify_makers_collection(doc):
    makers = MakerUser.objects.filter(hierarchy=doc.owner.hierarchy)
    doc_view_url = settings.BASE_URL + doc.get_absolute_url()

    MESSAGE_SUCC = f"""Dear Maker 
        The file named <a href='{doc_view_url}'>{doc.filename()}</a> was validated successfully 
        Thanks, BR"""

    subject = f'[{makers[0].brand.mail_subject}]'

    send_mail(
        from_email=settings.SERVER_EMAIL,
        recipient_list=[maker.email for maker in makers],
        subject= subject + _(' Collection File Upload Notification'),
        message=MESSAGE_SUCC
    )
