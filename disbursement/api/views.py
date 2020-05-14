import copy
import json
import logging

import environ
import requests
import xlrd

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import translation
from django.utils.translation import gettext as _

from rest_framework import status
from rest_framework.authentication import (SessionAuthentication, TokenAuthentication)
from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_expiring_authtoken.authentication import ExpiringTokenAuthentication

from data.models import Doc
from data.tasks import handle_change_profile_callback, notify_checkers
from users.models import CheckerUser, User

from ..models import Agent, DisbursementData, DisbursementDocData, VMTData
from ..utils import custom_budget_logger
from .permission_classes import BlacklistPermission
from .serializers import DisbursementCallBackSerializer, DisbursementSerializer


CHANGE_PROFILE_LOGGER = logging.getLogger("change_fees_profile")
DATA_LOGGER = logging.getLogger("disburse")

MSG_TRY_OR_CONTACT = "can you try again or contact you support team"
MSG_DISBURSEMENT_ERROR = _(f"Disbursement process stopped during an internal error, {MSG_TRY_OR_CONTACT}")
MSG_DISBURSEMENT_IS_RUNNING = _("Disbursement process is running, you can check reports later")


class DisburseAPIView(APIView):
    """
    Api for disbursing the data.
    The JSON sent to the external api:
    {
        "LOGIN"               : "",
        "PASSWORD"            : "",
        "REQUEST_GATEWAY_CODE": "",
        "REQUEST_GATEWAY_TYPE": "",
        "SERVICETYPE"         : "P2P",
        "TYPE"                : "PPREQ",
        "WALLETISSUER"        : "",
        "SENDERS"             : [
            {'MSISDN': "", 'PIN': ""},
            {'MSISDN': "", 'PIN': ""},
        ],
        "RECIPIENTS"          : [
            {'MSISDN': "", 'AMOUNT': "", 'TXNID': ""},
            {'MSISDN': "", 'AMOUNT': "", 'TXNID': ""},
        ]
    }
    """
    permission_classes = (BlacklistPermission,)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests to make a disbursement for a bulk of MSISDNs
        """
        env = environ.Env()
        import os
        from django.conf import settings
        environ.Env.read_env(env_file=os.path.join(settings.BASE_DIR, '.env'))

        # 1. Validate the serializer's data
        serializer = DisbursementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 2. Catch the corresponding vmt dictionary
        user = User.objects.get(username=serializer.validated_data['user'])
        superadmin = user.root.client.creator
        provider_id = Doc.objects.get(id=serializer.validated_data['doc_id']).owner.root.id

        # 3. Prepare the senders and recipients fields of the vmt dictionary
        pin = serializer.validated_data['pin']
        agents = Agent.objects.select_related().filter(wallet_provider_id=provider_id, super=False)
        senders = agents.extra(select={'MSISDN': 'msisdn'}).values('MSISDN')
        senders = list(senders)
        for internal_dict in senders:
            internal_dict.update({'PIN': pin})

        recipients = DisbursementData.objects.select_related('doc').filter(
                doc_id=serializer.validated_data['doc_id']
        ).extra(select={'MSISDN': 'msisdn', 'AMOUNT': 'amount', 'TXNID': 'id'}).values('MSISDN', 'AMOUNT', 'TXNID')

        payload = superadmin.vmt.accumulate_bulk_disbursement_payload(senders, list(recipients))

        payload_without_pins = copy.deepcopy(payload)
        for senders_dictionary in payload_without_pins['SENDERS']:
            senders_dictionary['PIN'] = 'xxxxxx'

        try:
            response = requests.post(env.str(superadmin.vmt.vmt_environment), json=payload, verify=False)
            DATA_LOGGER.debug(
                    "[DISBURSE BULK - REQUEST PAYLOAD]" + f"\nUser: {user}\nPayload: {str(payload_without_pins)}"
            )
            DATA_LOGGER.debug("[DISBURSE BULK - STATUS RESPONSE]" + f"\nStatus: {str(response.json())}")
        except ValueError:
            DATA_LOGGER.debug('[DISBURSE VALUE ERROR]' + f"\n{str(response.status_code)} -- {str(response.reason)}")
        except Exception as e:
            DATA_LOGGER.debug('[DISBURSE GENERAL ERROR]' + f"\nError{str(e)}")
            return HttpResponse(
                    json.dumps({'message': MSG_DISBURSEMENT_ERROR, 'header': _('Error occurred, We are sorry')}),
                    status=status.HTTP_424_FAILED_DEPENDENCY
            )

        if response.ok and response.json()["TXNSTATUS"] == '200':
            doc_obj = Doc.objects.get(id=serializer.validated_data['doc_id'])
            doc_obj.is_disbursed = True
            doc_obj.disbursed_by = user
            try:
                txn_status = response.json()["TXNSTATUS"]
                try:
                    txn_id = response.json()["BATCH_ID"]
                except KeyError:
                    txn_id = response.json()["TXNID"]
            except KeyError:
                return HttpResponse(
                        json.dumps({'message': MSG_DISBURSEMENT_ERROR, 'header': _('Error occurred, We are sorry')}),
                        status=status.HTTP_424_FAILED_DEPENDENCY
                )

            disb_data, create = DisbursementDocData.objects.get_or_create(doc=doc_obj)
            disb_data.txn_id = txn_id
            disb_data.txn_status = txn_status
            disb_data.save()
            doc_obj.save()
            return HttpResponse(
                    json.dumps({'message': MSG_DISBURSEMENT_IS_RUNNING, 'header': _('Disbursed, Thanks')}),
                    status=status.HTTP_200_OK
            )
        else:
            return HttpResponse(
                    json.dumps({'message': MSG_DISBURSEMENT_ERROR, 'header': _('Error occurred, We are sorry')}),
                    status=status.HTTP_424_FAILED_DEPENDENCY
            )
        #
        #     return HttpResponse(
        #         json.dumps({'message': _('Pin you entered is not correct'),
        #                     'header': _('Error occurred, We are sorry')}), status=status.HTTP_424_FAILED_DEPENDENCY)


class DisburseCallBack(UpdateAPIView):
    """
    API to receive disbursement transactions status from external api
    """
    serializer_class = DisbursementCallBackSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    renderer_classes = (JSONRenderer,)

    def update(self, request, *args, **kwargs):
        """
        Handles UPDATE requests coming from wallets as a callback to a disbursement request
            and UPDATES the budget record of the disbursed document Owner/Admin it he/she has custom budget
        """
        DATA_LOGGER.debug('[DISBURSE BULK - CALLBACK RESPONSE]' + f"\nCallback: {str(request.data)}")
        total_disbursed_amount = 0
        successfully_disbursed_obj = None

        if len(request.data['transactions']) == 0:
            return JsonResponse({'message': 'Transactions are empty'}, status=status.HTTP_404_NOT_FOUND)

        for data in request.data['transactions']:
            try:
                DisbursementData.objects.select_for_update().filter(id=int(data['id'])).update(
                        is_disbursed=True if data['status'] == '0' else False,
                        reason=data.get('description', 'No Description found')
                )

                # If data['status'] = 0, it means this record amount is disbursed successfully
                if data['status'] == '0':
                    successfully_disbursed_obj = DisbursementData.objects.get(id=int(data['id']))
                    total_disbursed_amount += int(successfully_disbursed_obj.amount)
            except DisbursementData.DoesNotExist:
                return JsonResponse({}, status=status.HTTP_404_NOT_FOUND)

        if successfully_disbursed_obj is not None and successfully_disbursed_obj.doc.owner.root.has_custom_budget:
            successfully_disbursed_obj.doc.owner.root.budget.update_disbursed_amount(total_disbursed_amount)
            custom_budget_logger(
                    successfully_disbursed_obj.doc.owner.root.username,
                    f"Total disbursed amount: {total_disbursed_amount} LE",
                    request.user.username, f" -- doc id: {successfully_disbursed_obj.doc_id}"
            )

        return JsonResponse({}, status=status.HTTP_202_ACCEPTED)


class ChangeProfileCallBack(UpdateAPIView):
    """
    API to receive Change profile transactions status from external wallet api
    """
    authentication_classes = (ExpiringTokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    renderer_classes = (JSONRenderer,)

    def update(self, request, *args, **kwargs):
        """
        Handles UPDATE requests coming from wallets as a callback to a change profile request
        """
        CHANGE_PROFILE_LOGGER.debug('[CHANGE PROFILE CALLBACK]\n' + f'Callback: {str(request.data)}')
        transactions = request.data.get('transactions', None)

        if not transactions:
            return JsonResponse({'message': 'Transactions are not sent'}, status=status.HTTP_404_NOT_FOUND)

        if len(transactions) == 0:
            return JsonResponse({'message': 'Transactions are empty'}, status=status.HTTP_404_NOT_FOUND)

        doc_obj = Doc.objects.filter(txn_id=request.data['batch_id']).first()

        if not doc_obj:
            return JsonResponse({'message': 'Batch id sent is not found'}, status=status.HTTP_404_NOT_FOUND)

        handle_change_profile_callback.delay(doc_obj.id, transactions)
        return JsonResponse({}, status=status.HTTP_202_ACCEPTED)


class RetrieveDocData(APIView):
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        try:
            doc_obj = Doc.objects.get(id=self.kwargs['doc_id'])
        except Doc.DoesNotExist:
            return JsonResponse({"message": _("Document is not found")}, status=status.HTTP_404_NOT_FOUND)

        xl_workbook = xlrd.open_workbook(doc_obj.file.path)
        xl_sheet = xl_workbook.sheet_by_index(0)
        excl_data = []
        position = None

        for row in xl_sheet.get_rows():
            row_data = []
            for x, data in enumerate(row):
                if not position:
                    position = x if data.value == doc_obj.file_category.amount_field else None
                row_data.append(data.value)
            excl_data.append(row_data)

        if position:
            return Response([excl_data, position], status=status.HTTP_200_OK)
        else:
            return Response([], status=status.HTTP_404_NOT_FOUND)


class AllowDocDisburse(APIView):
    """
    View for makers to Notify and allow the checkers that there is document ready for disbursement.
    """
    permission_classes = (IsAuthenticated,)
    authentication_classes = (SessionAuthentication,)
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests to send notification mails to checkers that there's new doc ready for review&disbursement
        """
        doc_obj = get_object_or_404(Doc, id=self.kwargs['doc_id'])

        if request.user.is_maker and doc_obj.is_processed:
            if doc_obj.can_be_disbursed:
                return JsonResponse({"message": _("Checkers already notified")}, status=status.HTTP_400_BAD_REQUEST)

            doc_obj.can_be_disbursed = True
            doc_obj.save()
            levels = CheckerUser.objects.filter(hierarchy=doc_obj.owner.hierarchy).values_list(
                'level__level_of_authority', flat=True
            )

            if not levels:
                return Response(status=status.HTTP_404_NOT_FOUND)

            # task for notifying checkers
            notify_checkers.delay(doc_obj.id,  min(list(levels)), language=translation.get_language())
            return Response(status=status.HTTP_200_OK)

        return Response(status=status.HTTP_403_FORBIDDEN)
