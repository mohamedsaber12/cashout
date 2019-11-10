# -*- coding: UTF-8 -*-
from __future__ import print_function

import json
import re
import tablib
import xlrd
import itertools
import requests
import logging
from datetime import datetime
from disbursement.utils import get_dot_env
from dateutil.parser import parse
from django.conf import settings
from django.utils.translation import gettext as _
from django.urls import reverse
from .models import Doc
from .models import FileData
from .utils import export_excel, randomword, deliver_mail
from .decorators import respects_language
from disb.models import DisbursementData, VMTData
from disb.resources import DisbursementDataResource
from disbursement.settings.celery import app
from users.models import User, MakerUser, CheckerUser


WALLET_API_LOGGER = logging.getLogger("wallet_api")
CHECKERS_NOTIFICATION_LOGGER = logging.getLogger("checkers_notification")


@app.task(ignore_result=False)
@respects_language
def handle_disbursement_file(doc_obj_id,**kwargs):
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
    rows = itertools.islice(xl_sheet.get_rows(), start_index, None)
    list_of_dicts = []
    for row, cell_obj in enumerate(rows,start_index):
        row_dict = {
            'amount':'',
            'error':'',
            'msisdn':''
        }
        for pos, item in enumerate(cell_obj):
            if pos == amount_position:
                try:
                    row_dict['amount'] = float(item.value)
                    if not row_dict['error']:
                        row_dict['error']  = None
                    
                except ValueError:
                    if row_dict['error']:
                        row_dict['error'] += '\nInvalid amount'
                    else:
                        row_dict['error'] = '\nInvalid amount'
                    row_dict['amount'] = item.value
                   
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
                    row_dict['msisdn'] = item.value
                    if row_dict['error']:
                        row_dict['error'] +=  "\nInvalid mobile number"
                    else:
                        row_dict['error'] = "Invalid mobile number"
                    
                # if msisdn is duplicate
                if list(filter(lambda d: d['msisdn'].replace(" ", "") == str_value.replace(" ", ""), list_of_dicts)):
                    row_dict['msisdn'] = item.value
                    if row_dict['error']:
                        row_dict['error'] += "\nDuplicate mobile number"
                    else:
                        row_dict['error'] = "Duplicate mobile number"
                  
                else:
                    if not row_dict['error']:
                        row_dict['error'] = None
                    row_dict['msisdn'] = str_value.replace(" ", "")
        
        list_of_dicts.append(row_dict)
    
    msisdn,amount,errors = [],[],[]
    for dict in list_of_dicts:
        msisdn.append(dict['msisdn'])
        amount.append(dict['amount'])
        errors.append(dict['error'])

    valid = True
    for item in errors:
        if item is not None:
            valid = False 
            break

    if not valid:
        filename = 'failed_disbursement_validation_%s.xlsx' % (
             randomword(4))

        file_path = "%s%s%s" % (settings.MEDIA_ROOT,
                            "/documents/disbursement/", filename)

        data = list(zip(amount, msisdn,errors))
        headers = ['amount','mobile number', 'errors']
        data.insert(0,headers)
        export_excel(file_path, data)
        download_url = settings.BASE_URL + \
            str(reverse('disbursement:download_validation_failed', kwargs={'doc_id': doc_obj_id})) + \
            '?filename=' + filename
        doc_obj.is_processed = False
        doc_obj.processing_failure_reason = _("File validation error")
        doc_obj.save()
        notify_maker(doc_obj, download_url)
        return False
    

    env = get_dot_env()
    reponse_dict = None
    if env.str('CALL_WALLETS', 'TRUE') == 'TRUE':      
        superadmin = doc_obj.owner.root.client.creator
        vmt = VMTData.objects.get(vmt=superadmin)
        data = vmt.return_vmt_data(VMTData.CHANGE_PROFILE)
        data["USERS"] = msisdn
        data["NEWPROFILE"] = doc_obj.owner.root.client.get_fees()
        try:
            response = requests.post(env.str(vmt.vmt_environment), json=data, verify=False)
        except Exception as e:
            WALLET_API_LOGGER.debug(f"""
            {datetime.now().strftime('%d/%m/%Y %H:%M')}----> CHANGE PROFILE ERROR<--
            Users-> maker:{doc_obj.owner.username}, vmt(superadmin):{superadmin.username}
            Error-> {e}""")
            doc_obj.is_processed = False
            doc_obj.processing_failure_reason = _("Registration process stopped during an internal error,\
                    can you try again or contact your support team")
            doc_obj.save()
            notify_maker(doc_obj)
            return False

        WALLET_API_LOGGER.debug(f"""
        {datetime.now().strftime('%d/%m/%Y %H:%M')}----> CHANGE PROFILE <--
        Users-> maker:{doc_obj.owner.username}, vmt(superadmin):{superadmin.username}
        Response-> {str(response.status_code)} -- {str(response.text)}""")
        error_message = None
        if response.ok:
            reponse_dict = response.json()
            if reponse_dict["TXNSTATUS"] != '200':
                error_message = reponse_dict.get('MESSAGE', None) or _(
                    "Failed to make registration")
                
        else:
            error_message = _("Registration process stopped during an internal error,\
                    can you try again or contact your support team")
        if error_message:
            doc_obj.is_processed = False
            doc_obj.processing_failure_reason = error_message
            doc_obj.save()
            notify_maker(doc_obj)
            return False

        doc_obj.is_processed = True
        notify_maker(doc_obj)
    else:
        error_message = _("Registration process stopped during an internal error,\
                            can you try again or contact your support team")
        doc_obj.is_processed = False
        doc_obj.processing_failure_reason = error_message
        doc_obj.save()
        notify_maker(doc_obj)
        return False

    data = zip(amount, msisdn)        
    DisbursementData.objects.bulk_create(
        [DisbursementData(doc=doc_obj, amount=float(
            i[0]), msisdn=i[1]) for i in data]
    )
    doc_obj.total_amount = sum(amount)
    doc_obj.total_count = len(amount)
    doc_obj.txn_id = reponse_dict['BATCH_ID'] if reponse_dict else None
    doc_obj.save()
    return True


@app.task()
def handle_change_profile_callback(doc_id,transactions):
    """realted to disbursement"""
    doc_obj = Doc.objects.get(id=doc_id)
    msisdns,errors = [],[]
    error = False
    for msisdn, status, msg_list in transactions:
        if status != "200" and status != "629":
            error = True
            errors.append('\n'.join(msg_list))
        else: 
            errors.append(None)    
        msisdns.append(msisdn)    
    if not error:
        doc_obj.is_processed = True
        doc_obj.save()
        notify_maker(doc_obj)
        return
    
    doc_obj.disbursement_data.all().delete()
    filename = 'failed_disbursement_validation_%s.xlsx' % (
        randomword(4))

    file_path = "%s%s%s" % (settings.MEDIA_ROOT,
                            "/documents/disbursement/", filename)

    data = list(zip(msisdns, errors))
    headers = ['mobile number', 'errors']
    data.insert(0, headers)
    export_excel(file_path, data)
    download_url = settings.BASE_URL + \
        str(reverse('disbursement:download_validation_failed', kwargs={'doc_id': doc_id})) + \
        '?filename=' + filename
    doc_obj.is_processed = False
    doc_obj.processing_failure_reason = _("Mobile numbers validation error")
    doc_obj.save()
    notify_maker(doc_obj, download_url)
    return


@app.task()
@respects_language
def generate_failed_disbursed_data(doc_id, user_id, **kwargs):
    """related to disbursement"""

    doc_obj = Doc.objects.get(id=doc_id)
    filename = _('failed_disbursed_%s_%s.xlsx') % (str(doc_id), randomword(4))

    dataset = DisbursementDataResource(
        file_category=doc_obj.file_category,
        doc=doc_obj,
        is_disbursed=False
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

    message = _(f"""Dear <strong>{str(user.first_name).capitalize()}</strong><br><br> 
        You can download the failed disbursement data related to this document
        <a href="{disb_doc_view_url}" >{doc_obj.filename()}</a>
        from here <a href="{download_url}" >Download</a><br><br>
        Thanks, BR""")
    deliver_mail(user, _(' Failed Disbursement File Download'), message)


@app.task()
@respects_language
def generate_success_disbursed_data(doc_id, user_id, **kwargs):
    """related to disbursement"""

    doc_obj = Doc.objects.get(id=doc_id)
    filename = _('success_disbursed_%s_%s.xlsx') % (str(doc_id), randomword(4))

    dataset = DisbursementDataResource(
        file_category=doc_obj.file_category,
        doc=doc_obj,
        is_disbursed=True
    )
    dataset = dataset.export()
    file_path = "%s%s%s" % (settings.MEDIA_ROOT,
                            "/documents/disbursement/", filename)
    with open(file_path, "wb") as f:
        f.write(dataset.xlsx)

    user = User.objects.get(id=user_id)
    disb_doc_view_url = settings.BASE_URL + \
        str(reverse('disbursement:disbursed_data', kwargs={'doc_id': doc_id}))

    download_url = settings.BASE_URL + \
        str(reverse('disbursement:download_failed', kwargs={'doc_id': doc_id})) + \
        '?filename=' + filename

    message = _(f"""Dear <strong>{str(user.first_name).capitalize()}</strong><br><br> 
        You can download the success disbursement data related to this document
        <a href="{disb_doc_view_url}" >{doc_obj.filename()}</a>
        from here <a href="{download_url}" >Download</a><br><br>
        Thanks, BR""")
    deliver_mail(user, _(' Success Disbursement File Download'), message)


@app.task()
@respects_language
def generate_all_disbursed_data(doc_id, user_id, **kwargs):
    """related to disbursement.
        generate success and failed disbursed data
    """

    doc_obj = Doc.objects.get(id=doc_id)
    filename = _('disbursed_data_%s_%s.xlsx') % (str(doc_id), randomword(4))

    dataset = DisbursementDataResource(
        file_category=doc_obj.file_category,
        doc=doc_obj,
        is_disbursed=None
    )
    dataset = dataset.export()
    file_path = "%s%s%s" % (settings.MEDIA_ROOT,
                            "/documents/disbursement/", filename)
    with open(file_path, "wb") as f:
        f.write(dataset.xlsx)

    user = User.objects.get(id=user_id)
    disb_doc_view_url = settings.BASE_URL + \
        str(reverse('disbursement:disbursed_data', kwargs={'doc_id': doc_id}))

    download_url = settings.BASE_URL + \
        str(reverse('disbursement:download_failed', kwargs={'doc_id': doc_id})) + \
        '?filename=' + filename

    message = _(f"""Dear <strong>{str(user.first_name).capitalize()}</strong><br><br>
        You can download the disbursement data related to this document
        <a href="{disb_doc_view_url}" >{doc_obj.filename()}</a>
        from here <a href="{download_url}" >Download</a><br><br>
        Thanks, BR""")
    deliver_mail(user, _(' Disbursement Data File Download'), message)


@app.task(ignore_result=False)
@respects_language
def handle_uploaded_file(doc_obj_id, **kwargs):
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
            file_data.date = datetime.now()
        file_data.save()
        
    doc_obj.is_processed = True
    doc_obj.save()
    notify_makers_collection(doc_obj)


@app.task()
@respects_language
def notify_checkers(doc_id, level, **kwargs):
    """related to disbursement"""
    doc_obj  = Doc.objects.get(id=doc_id)
    checkers = CheckerUser.objects.filter(
        hierarchy=doc_obj.owner.hierarchy).filter(level__level_of_authority=level)
    if not checkers.exists():
        return

    doc_view_url = settings.BASE_URL + doc_obj.get_absolute_url()
    message      = _(f"""Dear <strong>Checker</strong><br><br> 
        The file named <a href="{doc_view_url}" >{doc_obj.filename()}</a> is ready for disbursement<br><br>
        Thanks, BR""")
    deliver_mail(None, _(' Disbursement Notification'), message, checkers)

    CHECKERS_NOTIFICATION_LOGGER.debug(f"""{datetime.now().strftime('%d/%m/%Y %H:%M')}----------->
    checkers: {" and ".join([checker.username for checker in checkers])}
    vmt(superadmin):{doc_obj.owner.root.client.creator}
    """)


@app.task()
@respects_language
def doc_review_maker_mail(doc_id, review_id, **kwargs):
    """related to disbursement"""
    doc = Doc.objects.get(id=doc_id)
    review = doc.reviews.get(id=review_id)
    maker = doc.owner
    doc_view_url = settings.BASE_URL + doc.get_absolute_url()
    if review.is_ok:
        message = _(f"""Dear <strong>{str(maker.first_name).capitalize()}</strong><br><br>
            The file named <a href="{doc_view_url}" >{doc.filename()}</a> passed the review 
            number {doc.reviews.filter(is_ok=True).count()} out of {doc.file_category.no_of_reviews_required} by
            the checker: {review.user_created.first_name} {review.user_created.last_name}<br><br>
            Thanks, BR""")
    else:
        message = _(f"""Dear <strong>{str(maker.first_name).capitalize()}</strong><br><br>
                    The file named <a href="{doc_view_url}" >{doc.filename()}</a> didn't pass the review by
                    the checker: {review.user_created.first_name} {review.user_created.last_name}
                    and the reason is: {review.comment}<br><br>
                    Thanks, BR""")
    deliver_mail(maker, _(' File Upload Notification'), message)


def notify_maker(doc, download_url=None):
    """related to disbursement"""
    maker = doc.owner
    doc_view_url = settings.BASE_URL + doc.get_absolute_url()

    message = '' 
    if doc.is_processed:
        message = _(f"""Dear <strong>{str(maker.first_name).capitalize()}</strong><br><br> 
            The file named <a href="{doc_view_url}" >{doc.filename()}</a> was validated successfully 
            You can now notify checkers,<br><br>
            Thanks, BR""")
    else:
        MSG = _(f"""Dear <strong>{str(maker.first_name).capitalize()}</strong><br><br>
                The file named <a href="{doc_view_url}" >{doc.filename()}</a> failed validation
                The reason is: {doc.processing_failure_reason}""")

        if download_url:
            message = _(f"""{MSG}
                You can download the file containing errors from <a href="{download_url}" >here</a><br><br>
                Thanks, BR""")
        else:
            message = _(f"""{MSG}<br><br>
                Thanks, BR""")

    deliver_mail(maker, _(' File Upload Notification'), message)


def notify_makers_collection(doc):
    makers       = MakerUser.objects.filter(hierarchy=doc.owner.hierarchy)
    doc_view_url = settings.BASE_URL + doc.get_absolute_url()
    message      = _(f"""Dear <strong>Maker</strong><br><br> 
        The file named <a href="{doc_view_url}" >{doc.filename()}</a> was validated successfully<br><br>
        Thanks, BR""")
    deliver_mail(None, _(' Collection File Upload Notification'), message, makers)
