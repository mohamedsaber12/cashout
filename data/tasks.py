# -*- coding: UTF-8 -*-
from __future__ import print_function

import tablib
import xlrd
from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError

from data.models import Doc
from disb.models import DisbursementData
from disb.resources import DisbursementDataResource
from disbursement.settings.celery import app
from users.models import User


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
    amount_position, msisdn_position = 0, 0
    amount_field = doc_obj.file_category.amount_field
    msisdn_field = doc_obj.file_category.unique_field
    amount, msisdn = [], []
    for row, cell_obj in enumerate(xl_sheet.get_rows()):
        if row == 0:
            headers = [data.value for data in cell_obj]
            for pos, header in enumerate(headers):
                if header == amount_field:
                    amount_position = pos
                elif header == msisdn_field:
                    msisdn_position = pos
                else:
                    continue
            continue
        for pos, item in enumerate(cell_obj):
            if pos == amount_position:
                try:
                    amount.append(float(item.value))
                except ValueError:
                    doc_obj.is_processed = False
                    doc_obj.processing_failure_reason = "This file may be has invalid amounts"
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
                    doc_obj.processing_failure_reason = "This file may be has invalid msisdns"
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
            doc_obj.processing_failure_reason = "This file contains duplicates"
            doc_obj.save()
            notify_maker(doc_obj)
            return False
    else:
        doc_obj.is_processed = False
        doc_obj.processing_failure_reason = "This file may be has msisdn which has no amount"
        doc_obj.save()
        notify_maker(doc_obj)
        return False


@app.task()
def generate_file(doc_id):
    doc_obj = Doc.objects.get(id=doc_id)
    filename = 'failed_disbursed_%s.xlsx' % str(doc_id)

    dataset = DisbursementDataResource(
        file_category=doc_obj.file_category,
        doc=doc_obj
    )
    dataset = dataset.export('xlsx')
    with open("%s%s%s" % (settings.MEDIA_ROOT, "/disbursement/", filename), "w+") as f:
        f.writelines(dataset.get_xlsx())

    return filename
#
# @app.task()
# def send_disbursement_notification():


@app.task()
def notify_checkers(doc_id):
    doc_obj = Doc.objects.get(id=doc_id)
    checkers = User.objects.get_all_checkers(doc_obj.owner.hierarchy)
    if not checkers.exists():
        return

    doc_view_url = settings.BASE_URL + doc_obj.get_absolute_url()
    message = f"""Dear Checker 
        The file named <a href='{doc_view_url}'>{doc_obj.filename()}</a> is ready for disbursement
        Thanks, BR"""
    send_mail(
        from_email=settings.SERVER_EMAIL,
        recipient_list=[checker.email for checker in checkers],
        subject='[Payroll] Disbursement Notification',
        message=message
    )


def notify_maker(doc):
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

    send_mail(
        from_email=settings.SERVER_EMAIL,
        recipient_list=[maker.email],
        subject='[Payroll] File Upload Notification',
        message=message
    )
