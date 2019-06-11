import json
import logging
from datetime import datetime

import environ
import requests
import xlrd
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.utils import translation

from rest_framework import status
from rest_framework.authentication import TokenAuthentication,SessionAuthentication
from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_expiring_authtoken.authentication import ExpiringTokenAuthentication

from data.models import Doc
from data.tasks import notify_checkers,handle_change_profile_callback
from disb.api.permission_classes import BlacklistPermission
from disb.api.serializers import (DisbursementCallBackSerializer,
                                  DisbursementSerializer)
from disb.models import Agent, DisbursementData, DisbursementDocData, VMTData
from users.models import User

DATA_LOGGER = logging.getLogger("disburse")


class DisburseAPIView(APIView):
    """
    Api for disbursing the data.
    The JSON sent to the external api:
    {
        "LOGIN": "",
        "PASSWORD": "",
        "REQUEST_GATEWAY_CODE": "",
        "REQUEST_GATEWAY_TYPE": "",
        "SERVICETYPE": "P2P",
        "TYPE": "BPREQ",
        "WALLETISSUER": "",
        "SENDERS": [
            {'MSISDN': "",'PIN': ""},
        ],
        "RECIPIENTS": [
            {'MSISDN':"", 'AMOUNT':"", 'TXNID':""},
        ]
    }
    """
    permission_classes = (BlacklistPermission,)

    def post(self, request, *args, **kwargs):
        env = environ.Env()
        import os
        from django.conf import settings
        environ.Env.read_env(env_file=os.path.join(settings.BASE_DIR, '.env'))
        serializer = DisbursementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get(username=serializer.validated_data['user'])
        vmt = VMTData.objects.get(vmt=user.root.client.creator)
        provider_id = Doc.objects.get(
            id=serializer.validated_data['doc_id']).owner.root.id
        pin = serializer.validated_data['pin']
        agents = Agent.objects.select_related().filter(wallet_provider_id=provider_id)
        senders = agents.extra(
            select={'MSISDN': 'msisdn'}).values('MSISDN')
        senders = list(senders)
        for d in senders:
            d.update({'PIN': pin})
        recepients = DisbursementData.objects.select_related('doc').filter(doc_id=serializer.validated_data['doc_id']).\
            extra(select={'MSISDN': 'msisdn', 'AMOUNT': 'amount', 'TXNID': 'id'}).values(
                'MSISDN', 'AMOUNT', 'TXNID')
        data = vmt.return_vmt_data(VMTData.DISBURSEMENT)

        data.update({
            "SENDERS": senders,
            "RECIPIENTS": list(recepients),
        })

        response = requests.post(
            env.str(vmt.vmt_environment), json=data, verify=False)
        try:
            DATA_LOGGER.debug(datetime.now().strftime(
                '%d/%m/%Y %H:%M') + '----> DISBURSE <-- \n' + str(response.json()))
        except ValueError:
            DATA_LOGGER.debug(datetime.now().strftime('%d/%m/%Y %H:%M') + '----> DISBURSE ERROR <-- \n' +
                                str(response.status_code) + ' -- ' + str(response.reason))

        if response.ok and response.json()["TXNSTATUS"] == '200':
            doc_obj = Doc.objects.get(
                id=serializer.validated_data['doc_id'])
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
                    json.dumps({'message': _('Disbursement process stopped during an internal error,\
                        can you try again or contact your support team'),
                                'header': _('Error occurred, We are sorry')}), status=status.HTTP_424_FAILED_DEPENDENCY)


            disb_data, create = DisbursementDocData.objects.get_or_create(
                doc=doc_obj)
            disb_data.txn_id = txn_id
            disb_data.txn_status = txn_status
            disb_data.save()
            doc_obj.save()
            return HttpResponse(json.dumps({'message': _('Disbursement process is running, you can check reports later'),
                                            'header': _('Disbursed, Thanks')}), status=200)
        else:
            return HttpResponse(json.dumps({'message': _('Disbursement process stopped during an internal error,\
                can you try again or contact you support team'),
                                            'header': _('Error occurred, We are sorry')}), status=status.HTTP_424_FAILED_DEPENDENCY)
        # 
        #     return HttpResponse(
        #         json.dumps({'message': _('Pin you entered is not correct'),
        #                     'header': _('Error occurred, We are sorry')}), status=status.HTTP_424_FAILED_DEPENDENCY)


class DisburseCallBack(UpdateAPIView):
    """
    API to receive disbursment transactions status from external api
    """
    serializer_class = DisbursementCallBackSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    renderer_classes = (JSONRenderer,)

    def update(self, request, *args, **kwargs):
        DATA_LOGGER.debug(datetime.now().strftime(
            '%d/%m/%Y %H:%M') + '----> DISBURSE CALLBACK <-- \n' + str(request.data))
        if len(request.data['transactions']) == 0:
            return JsonResponse({'message': 'Transactions are empty'}, status=status.HTTP_404_NOT_FOUND)

        for data in request.data['transactions']:
            try:
                DisbursementData.objects.select_for_update().filter(id=int(data['id'])).update(
                    is_disbursed=True if data['status'] == '0' else False,
                    reason=data.get('description', 'No Description found')
                )
            except DisbursementData.DoesNotExist:
                return JsonResponse({}, status=status.HTTP_404_NOT_FOUND)

        return JsonResponse({}, status=status.HTTP_202_ACCEPTED)


class ChangeProfileCallBack(UpdateAPIView):
    """
    API to receive Change profile transactions status from external wallet api
    """
    authentication_classes = (ExpiringTokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    renderer_classes = (JSONRenderer,)

    def update(self, request, *args, **kwargs):
        DATA_LOGGER.debug(datetime.now().strftime(
            '%d/%m/%Y %H:%M') + '----> CHANGE PROFILE CALLBACK <-- \n' + str(request.data))
        transactions = request.data.get('transactions',None)
        if not transactions:
            return JsonResponse({'message': 'Transactions are not sent'}, status=status.HTTP_404_NOT_FOUND)
        if len(request.data['transactions']) == 0:
            return JsonResponse({'message': 'Transactions are empty'}, status=status.HTTP_404_NOT_FOUND)
        doc_obj = Doc.objects.filter(txn_id=request.data['batch_id']).first()
        if not doc_obj:
            return JsonResponse({}, status=status.HTTP_404_NOT_FOUND)
        handle_change_profile_callback.delay(doc_obj.id,request.data['transactions'])
        return JsonResponse({}, status=status.HTTP_202_ACCEPTED)


class RetrieveDocData(APIView):
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        try:
            doc_obj = Doc.objects.get(id=self.kwargs['doc_id'])
        except Doc.DoesNotExist:
            return JsonResponse({"message": _("Document is not found")}, status=404)
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
            return Response([excl_data, position], status=200)
        else:
            return Response([], status=404)


class AllowDocDisburse(APIView):
    """
    View for makers to Notify and allow the checkers that there is document ready for dibursment. 
    """
    permission_classes = (IsAuthenticated,)
    authentication_classes = (SessionAuthentication,)
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        doc_obj = get_object_or_404(Doc, id=self.kwargs['doc_id'])
        if request.user.is_maker and doc_obj.is_processed:
            if doc_obj.can_be_disbursed:
                return JsonResponse({"message": _("Checkers already notified")}, status=400)
            doc_obj.can_be_disbursed = True
            doc_obj.save()
            # task for notifying checkers
            notify_checkers.delay(
                doc_obj.id, 1, language=translation.get_language())
            return Response(status=200)

        return Response(status=403)
