import json
import logging

from requests.exceptions import HTTPError
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
from data.utils import get_client_ip
from users.models import CheckerUser, User
from utilities.custom_requests import CustomRequests
from utilities.functions import custom_budget_logger, get_value_from_env
from utilities.messages import MSG_DISBURSEMENT_ERROR, MSG_DISBURSEMENT_IS_RUNNING, MSG_PIN_INVALID

from ..models import Agent, DisbursementData, DisbursementDocData
from .permission_classes import BlacklistPermission
from .serializers import DisbursementCallBackSerializer, DisbursementSerializer
from ..tasks import BulkDisbursementThroughOneStepCashin


CHANGE_PROFILE_LOGGER = logging.getLogger("change_fees_profile")
DATA_LOGGER = logging.getLogger("disburse")

DISBURSEMENT_ERR_RESP_DICT = {'message': _(MSG_DISBURSEMENT_ERROR), 'header': _('Error occurred, We are sorry')}
DISBURSEMENT_RUNNING_RESP_DICT = {'message': _(MSG_DISBURSEMENT_IS_RUNNING), 'header': _('Disbursed, Thanks')}


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
    permission_classes = [BlacklistPermission]

    @staticmethod
    def prepare_agents_list(provider, raw_pin):
        """
        :param provider: wallet provider user
        :return: tuple of vodafone agent, etisalat agents lists
        """
        if provider.is_accept_vodafone_onboarding:
            agents = Agent.objects.filter(wallet_provider=provider.super_admin, super=False)
        else:
            agents = Agent.objects.filter(wallet_provider=provider, super=False)
        vodafone_agents = agents.filter(type=Agent.VODAFONE)
        etisalat_agents = agents.filter(type=Agent.ETISALAT)

        vodafone_agents = vodafone_agents.extra(select={'MSISDN': 'msisdn'}).values('MSISDN')
        etisalat_agents = etisalat_agents.values_list('msisdn', flat=True)

        vodafone_agents = list(vodafone_agents)
        for internal_dict in vodafone_agents:
            internal_dict.update({'PIN': raw_pin})

        return vodafone_agents, list(etisalat_agents)

    def prepare_vodafone_recipients(self, doc_id):
        """
        :param doc_id: Id of the document being disbursed
        :return: vodafone recipients
        """
        vf_recipients = DisbursementData.objects.filter(doc_id=doc_id, issuer__in=['vodafone', 'default']).\
            extra(select={'MSISDN': 'msisdn', 'AMOUNT': 'amount', 'TXNID': 'id'}).values('MSISDN', 'AMOUNT', 'TXNID')

        return list(vf_recipients)

    @staticmethod
    def disburse_for_recipients(url, payload, username, refined_payload, jsoned_response=False):
        """
        Disburse for issuer based recipients
        :param url: wallets environment that will handle the disbursement request
        :param payload: request payload to be sent
        :param username: checker user who is disbursing the current document used at logging
        :param refined_payload: payload without pins to be used at logging
        :param jsoned_response: flag to check if the response needed as json of raw response object
        :return: response object if successful disbursement or False
        """
        logging_header = "BULK DISBURSEMENT TO CENTRAL UIG"
        DATA_LOGGER.debug(f"[request] [{logging_header}] [{username}] -- {refined_payload}")
        request_obj = CustomRequests()

        try:
            response = request_obj.post(url=url, payload=payload)
            DATA_LOGGER.debug(f"[response] [{logging_header}] [{username}] -- {request_obj.resp_log_msg}")
            return response.json() if jsoned_response else response
        except (HTTPError, ConnectionError, Exception):
            DATA_LOGGER.debug(f"[response] [{logging_header}] [{username}] -- {request_obj.resp_log_msg}")
            return False

    def determine_disbursement_status(self, checker_user, doc_obj, vf_response, temp_response):
        """
        Determine document disbursement status based on the disbursement response
        :param checker_user: user who triggered the disbursement request
        :param doc_obj: document object being disbursed
        :param vf_response: disbursement response object for vodafone recipients
        :param temp_response: disbursement response to wait for bulk disbursement task to finish
        :return: True/False
        """
        for response in [vf_response, temp_response]:

            if type(response) == dict and response["TXNSTATUS"] == '200':
                try:
                    txn_status = response["TXNSTATUS"]
                    try:
                        txn_id = response["BATCH_ID"]
                    except KeyError:
                        txn_id = response["TXNID"]
                except KeyError:
                    doc_obj.mark_disbursement_failure()
                    return False

                doc_obj.mark_disbursed_successfully(checker_user, txn_id, txn_status)
                return True

        doc_obj.mark_disbursement_failure()
        return False

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests to make a disbursement for a bulk of MSISDNs
        """

        # 1. Validate the serializer's data
        serializer = DisbursementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc_obj = Doc.objects.get(id=serializer.validated_data['doc_id'])

        pin = serializer.validated_data['pin']
        if doc_obj.owner.root.pin != 'False' and not doc_obj.owner.root.check_pin(pin):
            return HttpResponse(
                    json.dumps({'message': MSG_PIN_INVALID, 'header': 'Error occurred from your side!'}),
                    status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Catch the corresponding vmt dictionary
        checker = User.objects.get(username=serializer.validated_data['user'])
        superadmin = checker.root.client.creator
        wallets_env_url = get_value_from_env(superadmin.vmt.vmt_environment)
        vf_response = False
        temp_response = {'BATCH_ID': '0', 'TXNSTATUS': '200'}

        # 3. Prepare the senders and recipients list of dictionaries
        vf_recipients = self.prepare_vodafone_recipients(doc_obj.id)

        if vf_recipients:
            if checker.root.is_accept_vodafone_onboarding:
                pin = get_value_from_env(f"{superadmin.username}_VODAFONE_PIN")
            vf_agents, _ = self.prepare_agents_list(provider=checker.root, raw_pin=pin)
            vf_payload, vf_log_payload = superadmin.vmt.accumulate_bulk_disbursement_payload(vf_agents, vf_recipients)
            vf_response = self.disburse_for_recipients(wallets_env_url, vf_payload, checker, vf_log_payload, True)

        BulkDisbursementThroughOneStepCashin.delay(
                doc_id=str(doc_obj.id), checker_username=str(checker.username), ip_address=str(get_client_ip(request))
        )
        is_success_disbursement = self.determine_disbursement_status(checker, doc_obj, vf_response, temp_response)

        if is_success_disbursement:
            return HttpResponse(json.dumps(DISBURSEMENT_RUNNING_RESP_DICT), status=status.HTTP_200_OK)
        else:
            return HttpResponse(json.dumps(DISBURSEMENT_ERR_RESP_DICT), status=status.HTTP_424_FAILED_DEPENDENCY)


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
        DATA_LOGGER.debug(f"[response] [BULK DISBURSEMENT CALLBACK] [{request.user}] -- {str(request.data)}")
        total_disbursed_amount = 0
        last_doc_record_id = successfully_disbursed_obj = None

        if len(request.data['transactions']) == 0:
            return JsonResponse({'message': 'Transactions are empty'}, status=status.HTTP_404_NOT_FOUND)

        for data in request.data['transactions']:
            try:
                last_doc_record_id = int(data['id'])
                DisbursementData.objects.select_for_update().filter(id=int(data['id'])).update(
                        is_disbursed=True if data['status'] == '0' else False,
                        reason=data.get('description', 'No Description found'),
                        reference_id=data.get('mpg_rrn', 'None')
                )

                # If data['status'] = 0, it means this record amount is disbursed successfully
                if data['status'] == '0':
                    successfully_disbursed_obj = DisbursementData.objects.get(id=int(data['id']))
                    total_disbursed_amount += int(successfully_disbursed_obj.amount)
            except DisbursementData.DoesNotExist:
                return JsonResponse({}, status=status.HTTP_404_NOT_FOUND)

        if successfully_disbursed_obj is not None and successfully_disbursed_obj.doc.owner.root.has_custom_budget:
            successfully_disbursed_obj.doc.owner.root.budget.\
                update_disbursed_amount_and_current_balance(total_disbursed_amount, "vodafone")
            custom_budget_logger(
                    successfully_disbursed_obj.doc.owner.root.username,
                    f"Total disbursed amount: {total_disbursed_amount} LE",
                    request.user.username, f" -- doc id: {successfully_disbursed_obj.doc_id}"
            )

        if last_doc_record_id:
            DisbursementDocData.objects.filter(doc__disbursement_data__id=last_doc_record_id).update(has_callback=True)

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
        CHANGE_PROFILE_LOGGER.debug(f"[response] [CHANGE PROFILE CALLBACK] [{request.user}] -- {str(request.data)}")
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
        current_user = request.user

        if current_user.is_maker and doc_obj.is_processed and doc_obj.owner == current_user:
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
