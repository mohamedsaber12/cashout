# -*- coding: UTF-8 -*-
from __future__ import print_function

import itertools
import json
import logging
import re
from datetime import datetime

import requests
import tablib
import xlrd
from dateutil.parser import parse

from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext as _

from disb.models import Budget, DisbursementData, VMTData
from disb.resources import DisbursementDataResource
from payouts.settings.celery import app
from payouts.utils import get_dot_env
from users.models import CheckerUser, Levels, UploaderUser, User

from .decorators import respects_language
from .models import Doc, FileData
from .utils import deliver_mail, export_excel, randomword


CHANGE_PROFILE_LOGGER = logging.getLogger("change_fees_profile")
WALLET_API_LOGGER = logging.getLogger("wallet_api")
CHECKERS_NOTIFICATION_LOGGER = logging.getLogger("checkers_notification")

MSG_TRY_OR_CONTACT = "can you try again or contact your support team"
MSG_NOT_WITHIN_THRESHOLD = _(f"Disbursement file's amounts exceeds your current balance, {MSG_TRY_OR_CONTACT}")
MSG_MAXIMUM_ALLOWED_AMOUNT_TO_BE_DISBURSED = _(
        f"Disbursement file's amounts exceeds your maximum amount that can be disbursed, {MSG_TRY_OR_CONTACT}")
MSG_REGISTRATION_PROCESS_ERROR = _(f"Registration process stopped during an internal error, {MSG_TRY_OR_CONTACT}")


@app.task(ignore_result=False)
@respects_language
def handle_disbursement_file(doc_obj_id, **kwargs):
    """
    A function that parse the document and save it into the File Data
    It has 3 cases :
    Category has files so check if draft or delete stale data
    Category has no files
    """
    doc_obj = Doc.objects.get(id=doc_obj_id)
    amount_to_be_disbursed_within_custom_budget_threshold = False
    amount_position, msisdn_position = doc_obj.file_category.fields_cols()
    start_index = doc_obj.file_category.starting_row()
    xl_workbook = xlrd.open_workbook(doc_obj.file.path)
    xl_sheet = xl_workbook.sheet_by_index(0)
    rows = itertools.islice(xl_sheet.get_rows(), start_index, None)
    list_of_dicts = []

    # ToDo: use Forms to validate excel sheet records instead of a lot of loops logic
    for row, cell_obj in enumerate(rows, start_index):
        row_dict = {'amount': '', 'error': '', 'msisdn': '', 'status': ''}

        for pos, item in enumerate(cell_obj):
            if pos == amount_position:
                try:
                    if item.value == '':
                        row_dict['error'] = '\nEmpty amount'
                    elif float(item.value) < 0.01:
                        row_dict['error'] = '\nInvalid amount'
                    else:
                        row_dict['amount'] = float(item.value)
                    if not row_dict['error']:
                        row_dict['error'] = None
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
                        row_dict['error'] += "\nInvalid mobile number"
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

        if row_dict['error'] is None:
            row_dict['status'] = 'valid'
        else:
            row_dict['status'] = 'invalid'
        list_of_dicts.append(row_dict)

    msisdn, amount, errors, status, partial_msisdn, partial_amount = [], [], [], [], [], []
    for dict in list_of_dicts:
        msisdn.append(dict['msisdn'])
        amount.append(dict['amount'])
        errors.append(dict['error'])
        status.append(dict['status'])
        if status[-1] == 'valid':
            partial_msisdn.append(dict['msisdn'])
            partial_amount.append(dict['amount'])

    valid = True
    partial_valid = False
    for item in errors:
        if item is not None:
            valid = False
            break

    for item in status:
        if item == 'valid':
            partial_valid = True
            break

    # Levels of file validations
    # 1, Uploaded file's total amount exceeds the maximum amount that can be disbursed
    # 2, Uploaded file's format is not consistent with the one chosen from the defined formats
    if errors[0] is not None:
        error_message = errors[0]
    else:
        error_message = None
    download_url = False

    if doc_obj.owner.root.has_custom_budget:
        amount_to_be_disbursed_within_custom_budget_threshold = Budget.objects.get(
                disburser=doc_obj.owner.root).within_threshold(sum(partial_amount))

    if valid or partial_valid:
        max_amount_can_be_disbursed = max(
            [level.max_amount_can_be_disbursed for level in Levels.objects.filter(created=doc_obj.owner.root)]
        )
        try:
            if sum(partial_amount) > max_amount_can_be_disbursed:
                error_message = MSG_MAXIMUM_ALLOWED_AMOUNT_TO_BE_DISBURSED
                valid = False
                partial_valid = False

            if doc_obj.owner.root.has_custom_budget and not amount_to_be_disbursed_within_custom_budget_threshold:
                error_message = MSG_NOT_WITHIN_THRESHOLD
                valid = False
                partial_valid = False
        except:
            error_message = _("Empty or Invalid Amount Numbers")
            valid = False
            partial_valid = False

    if not valid:
        filename = 'failed_disbursement_validation_%s.xlsx' % (randomword(4))
        file_path = "%s%s%s" % (settings.MEDIA_ROOT, "/documents/disbursement/", filename)
        if error_message is None:
            error_message = _("File validation error")
            data = list(zip(amount, msisdn, errors))
            headers = ['amount', 'mobile number', 'errors']
            data.insert(0, headers)
            export_excel(file_path, data)
            download_url = settings.BASE_URL + \
                str(reverse('disbursement:download_validation_failed', kwargs={'doc_id': doc_obj_id})) + \
                '?filename=' + filename
        doc_obj.is_processed = False
        doc_obj.processing_failure_reason = error_message
        doc_obj.save()
        notify_maker(doc_obj, download_url) if download_url else notify_maker(doc_obj)
        if not partial_valid:
            return False

    env = get_dot_env()
    response_dict = None
    if env.str('CALL_WALLETS', 'TRUE') == 'TRUE':
        superadmin = doc_obj.owner.root.client.creator
        vmt = VMTData.objects.get(vmt=superadmin)
        data = vmt.return_vmt_data(VMTData.CHANGE_PROFILE)
        data["USERS"] = partial_msisdn
        data["NEWPROFILE"] = doc_obj.owner.root.client.get_fees()
        try:
            response = requests.post(env.str(vmt.vmt_environment), json=data, verify=False)
        except Exception as e:
            CHANGE_PROFILE_LOGGER.debug(f"""[CHANGE PROFILE ERROR]
            Users: {doc_obj.owner.username}, superadmin:{superadmin.username}
            Error: {e}""")
            doc_obj.is_processed = False
            doc_obj.processing_failure_reason = MSG_REGISTRATION_PROCESS_ERROR
            doc_obj.save()
            notify_maker(doc_obj)
            return False

        CHANGE_PROFILE_LOGGER.debug(f"""[CHANGE PROFILE]
        Users: {doc_obj.owner.username}, superadmin: {superadmin.username}
        Response: {str(response.status_code)} -- {str(response.text)}""")
        error_message = None
        if response.ok:
            response_dict = response.json()
            if response_dict["TXNSTATUS"] != '200':
                error_message = response_dict.get('MESSAGE', None) or _("Failed to make registration")
        else:
            error_message = MSG_REGISTRATION_PROCESS_ERROR
        if error_message:
            doc_obj.is_processed = False
            doc_obj.processing_failure_reason = error_message
            doc_obj.save()
            notify_maker(doc_obj)
            return False

        doc_obj.is_processed = True
        notify_maker(doc_obj)
    else:
        error_message = MSG_REGISTRATION_PROCESS_ERROR
        doc_obj.is_processed = False
        doc_obj.processing_failure_reason = error_message
        doc_obj.save()
        notify_maker(doc_obj)
        return False

    data = zip(partial_amount, partial_msisdn)
    DisbursementData.objects.bulk_create(
            [DisbursementData(doc=doc_obj, amount=float(i[0]), msisdn=i[1]) for i in data]
    )
    doc_obj.total_amount = sum(partial_amount)
    doc_obj.total_count = len(partial_amount)
    doc_obj.txn_id = response_dict['BATCH_ID'] if response_dict else None
    doc_obj.save()
    return True


@app.task()
def handle_change_profile_callback(doc_id, transactions):
    """
    Related to disbursement
    Background task for handling central callback of msisdns change profile process
    :param doc_id: Id of the doc which holds the msisdns
    :param transactions: The callback dictionary from the central
    :return:
    """
    doc_obj = Doc.objects.get(id=doc_id)
    msisdns, errors = [], []
    error = False

    for msisdn, status, msg_list in transactions:
        if status not in ["200", "629", "560"]:
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
    filename = 'failed_disbursement_validation_%s.xlsx' % (randomword(4))
    file_path = "%s%s%s" % (settings.MEDIA_ROOT, "/documents/disbursement/", filename)

    data = list(zip(msisdns, errors))
    headers = ['mobile number', 'errors']
    data.insert(0, headers)
    export_excel(file_path, data)
    download_url = settings.BASE_URL + \
        str(reverse('disbursement:download_validation_failed', kwargs={'doc_id': doc_id})) + '?filename=' + filename
    doc_obj.is_processed = False
    doc_obj.processing_failure_reason = _("Mobile numbers validation error")
    doc_obj.save()
    notify_maker(doc_obj, download_url)
    return


@app.task()
@respects_language
def generate_failed_disbursed_data(doc_id, user_id, **kwargs):
    """
    Related to disbursement
    :param doc_id:
    :param user_id:
    :param kwargs:
    :return:
    """
    doc_obj = Doc.objects.get(id=doc_id)
    filename = _('failed_disbursed_%s_%s.xlsx') % (str(doc_id), randomword(4))

    dataset = DisbursementDataResource(
        file_category=doc_obj.file_category,
        doc=doc_obj,
        is_disbursed=False
    )
    dataset = dataset.export()
    file_path = "%s%s%s" % (settings.MEDIA_ROOT, "/documents/disbursement/", filename)
    with open(file_path, "wb") as f:
        f.write(dataset.xlsx)

    user = User.objects.get(id=user_id)
    disb_doc_view_url = settings.BASE_URL + str(reverse('disbursement:disbursed_data', kwargs={'doc_id': doc_id}))

    download_url = settings.BASE_URL + \
        str(reverse('disbursement:download_failed', kwargs={'doc_id': doc_id})) + '?filename=' + filename

    message = _(f"""Dear <strong>{str(user.first_name).capitalize()}</strong><br><br> 
        You can download the failed disbursement data related to this document
        <a href="{disb_doc_view_url}" >{doc_obj.filename()}</a>
        from here <a href="{download_url}" >Download</a><br><br>
        Thanks, BR""")
    deliver_mail(user, _(' Failed Disbursement File Download'), message)


@app.task()
@respects_language
def generate_success_disbursed_data(doc_id, user_id, **kwargs):
    """
    Related to disbursement
    :param doc_id:
    :param user_id:
    :param kwargs:
    :return:
    """
    doc_obj = Doc.objects.get(id=doc_id)
    filename = _('success_disbursed_%s_%s.xlsx') % (str(doc_id), randomword(4))

    dataset = DisbursementDataResource(
        file_category=doc_obj.file_category,
        doc=doc_obj,
        is_disbursed=True
    )
    dataset = dataset.export()
    file_path = "%s%s%s" % (settings.MEDIA_ROOT, "/documents/disbursement/", filename)
    with open(file_path, "wb") as f:
        f.write(dataset.xlsx)

    user = User.objects.get(id=user_id)
    disb_doc_view_url = settings.BASE_URL + str(reverse('disbursement:disbursed_data', kwargs={'doc_id': doc_id}))

    download_url = settings.BASE_URL + \
        str(reverse('disbursement:download_failed', kwargs={'doc_id': doc_id})) + '?filename=' + filename

    message = _(f"""Dear <strong>{str(user.first_name).capitalize()}</strong><br><br> 
        You can download the success disbursement data related to this document
        <a href="{disb_doc_view_url}" >{doc_obj.filename()}</a>
        from here <a href="{download_url}" >Download</a><br><br>
        Thanks, BR""")
    deliver_mail(user, _(' Success Disbursement File Download'), message)


@app.task()
@respects_language
def generate_all_disbursed_data(doc_id, user_id, **kwargs):
    """
    Related to disbursement
    Generate success and failed excel sheet from already disbursed data
    """
    doc_obj = Doc.objects.get(id=doc_id)
    filename = _('disbursed_data_%s_%s.xlsx') % (str(doc_id), randomword(4))

    dataset = DisbursementDataResource(
        file_category=doc_obj.file_category,
        doc=doc_obj,
        is_disbursed=None
    )
    dataset = dataset.export()
    file_path = "%s%s%s" % (settings.MEDIA_ROOT, "/documents/disbursement/", filename)
    with open(file_path, "wb") as f:
        f.write(dataset.xlsx)

    user = User.objects.get(id=user_id)
    disb_doc_view_url = settings.BASE_URL + str(reverse('disbursement:disbursed_data', kwargs={'doc_id': doc_id}))

    download_url = settings.BASE_URL + \
        str(reverse('disbursement:download_failed', kwargs={'doc_id': doc_id})) + '?filename=' + filename

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
    Related to collection
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
                file_data.date = parse(file_data.data[collection_data.date_field]).date()
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
    """
    Related to disbursement
    Background task to send email to the next level of checkers that this is your turn to review the file
    :param doc_id: the id of the document which needs to be reviewed
    :param level: Level of authoritative checkers, that determines which level has to review the file
    :param kwargs: Any other kwargs
    :return:
    """
    doc_obj = Doc.objects.get(id=doc_id)
    checkers = CheckerUser.objects.filter(hierarchy=doc_obj.owner.hierarchy).filter(level__level_of_authority=level)

    if not checkers.exists():
        return

    doc_view_url = settings.BASE_URL + doc_obj.get_absolute_url()
    message = _(f"""Dear <strong>Checker</strong><br><br> 
        The file named <a href="{doc_view_url}" >{doc_obj.filename()}</a> is ready for review<br><br>
        Thanks, BR""")
    deliver_mail(None, _(' Review Notification'), message, checkers)

    CHECKERS_NOTIFICATION_LOGGER.debug(f"""[REVIEWERS' NOTIFIED NOW]
    checkers: {" and ".join([checker.username for checker in checkers])}
    vmt(superadmin):{doc_obj.owner.root.client.creator}""")


@app.task()
@respects_language
def notify_disbursers(doc_id, min_level, **kwargs):
    """
    Related to disbursement
    Background task to send email to notify all levels of authoritative checkers that the file is ready for disbursement
    :param doc_id: the id of the document which passed the needed reviews successfully and is ready for disbursement
    :param min_level: Minimum level of authoritative checkers
    :param kwargs: Any other kwargs
    :return:
    """
    doc_obj = Doc.objects.get(id=doc_id)
    disbursers_to_be_notified = CheckerUser.objects.filter(hierarchy=doc_obj.owner.hierarchy).filter(
            level__level_of_authority__gte=min_level)

    if not disbursers_to_be_notified.exists():
        return

    doc_view_url = settings.BASE_URL + doc_obj.get_absolute_url()
    message = _(f"""Dear <strong>Checker</strong><br><br>
        The file named <a href="{doc_view_url}" >{doc_obj.filename()}</a> is ready for disbursement<br><br>
        Thanks, BR""")
    deliver_mail(None, _(' Disbursement Notification'), message, disbursers_to_be_notified)

    CHECKERS_NOTIFICATION_LOGGER.debug(f"""[DISBURSERS' NOTIFIED NOW]
    disbursers: {" and ".join([checker.username for checker in disbursers_to_be_notified])}
    vmt(superadmin):{doc_obj.owner.root.client.creator}""")


@app.task()
@respects_language
def doc_review_maker_mail(doc_id, review_id, **kwargs):
    """
    Related to disbursement
    Background task to send mail to maker users after the reviews have been completed
    :param doc_id:
    :param review_id:
    :param kwargs:
    :return:
    """
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
    deliver_mail(maker, _(' File Review Notification'), message)


def notify_maker(doc, download_url=None):
    """
    Related to disbursement
    :param doc:
    :param download_url:
    :return:
    """
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
    makers = UploaderUser.objects.filter(hierarchy=doc.owner.hierarchy)
    doc_view_url = settings.BASE_URL + doc.get_absolute_url()
    message = _(f"""Dear <strong>Maker</strong><br><br> 
        The file named <a href="{doc_view_url}" >{doc.filename()}</a> was validated successfully<br><br>
        Thanks, BR""")
    deliver_mail(None, _(' Collection File Upload Notification'), message, makers)
