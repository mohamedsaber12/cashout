from decimal import Decimal
from datetime import datetime
import json
import logging
from urllib import request
from data.utils import paginator
from rest_framework import status, viewsets
from instant_cashin.models import  InstantTransaction

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
from rest_framework.pagination import PageNumberPagination

from data.models import Doc
from data.tasks import handle_change_profile_callback, notify_checkers
from users.models import CheckerUser, User, Client
from utilities.custom_requests import CustomRequests
from utilities.functions import custom_budget_logger, get_value_from_env
from utilities.messages import MSG_DISBURSEMENT_ERROR, MSG_DISBURSEMENT_IS_RUNNING, MSG_PIN_INVALID

from ..models import Agent, DisbursementData, DisbursementDocData
from .permission_classes import BlacklistPermission
from .serializers import DisbursementCallBackSerializer, DisbursementSerializer, Merchantserializer
from ..tasks import BulkDisbursementThroughOneStepCashin
import requests
import json

from django.utils.timezone import datetime, make_aware
from users.models import (
    Client,  RootUser, User, Setup,
    EntitySetup)
from utilities.models import Budget, CallWalletsModerator, FeeSetup
from instant_cashin.utils import get_from_env
from utilities.logging import logging_message
from django.contrib.auth.models import Permission
from django.urls import reverse_lazy



ROOT_CREATE_LOGGER = logging.getLogger("root_create")
CHANGE_PROFILE_LOGGER = logging.getLogger("change_fees_profile")
DATA_LOGGER = logging.getLogger("disburse")
WALLET_API_LOGGER = logging.getLogger("wallet_api")


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
        :param raw_pin: the raw pin used at disbursement
        :return: tuple of vodafone agent, etisalat agents lists
        """
        if not (provider.is_vodafone_default_onboarding or provider.is_banks_standard_model_onboaring):
            agents = Agent.objects.filter(wallet_provider=provider.super_admin, super=False)
        else:
            agents = Agent.objects.filter(wallet_provider=provider)
            agents = agents.filter(super=True) if provider.client.agents_onboarding_choice == Client.P2M else \
                agents.filter(super=False)

        vodafone_agents = agents.filter(type=Agent.VODAFONE)
        etisalat_agents = agents.filter(type=Agent.ETISALAT)

        if agents.first().type == Agent.P2M and not vodafone_agents:
            vodafone_agents = agents.filter(type=Agent.P2M)

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

    def set_disbursed_date(self, doc_id):
        """
        :param doc_id: Id of the document being disbursed
        set disbursed date for all records related to doc ID
        """
        DisbursementData.objects.filter(doc_id=doc_id).update(disbursed_date=datetime.now())


    @staticmethod
    def disburse_for_recipients(url, payload, username, refined_payload, jsoned_response=False, txn_id=None):
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
        except (requests.Timeout, TimeoutError) as e:
            DATA_LOGGER.debug(f"[response Timeout] [Timeout FROM CENTRAL] [{username}] -- timeout:- {e.args}")
            if txn_id:
                current_trx = DisbursementData.objects.get(id=txn_id)
                current_trx.is_disbursed = False
                current_trx.disbursed_date=datetime.now()
                current_trx.save()
        except (HTTPError, ConnectionError, Exception):
            DATA_LOGGER.debug(f"[response error] [{logging_header}] [{username}] -- {request_obj.resp_log_msg}")
            return False

    @staticmethod
    def disburse_for_recipients_deposit(url, payload, username, refined_payload, inst_obj):
        """
        Disburse for issuer based recipients
        :param url: wallets environment that will handle the disbursement request
        :param payload: request payload to be sent
        :param username: checker user who is disbursing the current document used at logging
        :param refined_payload: payload without pins to be used at logging
        :param jsoned_response: flag to check if the response needed as json of raw response object
        :return: response object if successful disbursement or False
        """
        payload["WALLETISSUER"] = "VODAFONE"
        refined_payload["WALLETISSUER"] = "VODAFONE"
        payload["TYPE"] = "DPSTREQ"
        refined_payload["TYPE"] = "DPSTREQ"
        logging_header = "BULK DISBURSEMENT TO CENTRAL UIG"
        DATA_LOGGER.debug(f"[request] [{logging_header}] [{username}] -- {refined_payload}")
        request_obj = CustomRequests()

        try:
            response = request_obj.post(url=url, payload=payload)
            DATA_LOGGER.debug(f"[response] [{logging_header}] [{username}] -- {request_obj.resp_log_msg}")
            return response
        except (requests.Timeout, TimeoutError) as e:
            DATA_LOGGER.debug(f"[response Timeout] [Timeout FROM CENTRAL] [{username}] -- timeout:- {e.args}")
            inst_obj.mark_failed(status.HTTP_424_FAILED_DEPENDENCY, "Timeout request")
        except (HTTPError, ConnectionError, Exception):
            DATA_LOGGER.debug(f"[response error] [{logging_header}] [{username}] -- {request_obj.resp_log_msg}")
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

    def check_balance_before_disbursement(self, request, checker,doc_obj ):
        total_doc_amount = self.get_total_doc_amount(doc_obj)
        # get balance
        superadmin = checker.root.client.creator
        super_agent = Agent.objects.get(wallet_provider=checker.root, super=True)
        payload, refined_payload = superadmin.vmt.accumulate_balance_inquiry_payload(super_agent.msisdn, pin)

        try:
            WALLET_API_LOGGER.debug(f"[request] [BALANCE INQUIRY] [{request.user}] -- {refined_payload}")
            response = requests.post(env.str(superadmin.vmt.vmt_environment), json=payload, verify=False)
        except Exception as e:
            WALLET_API_LOGGER.debug(f"[message] [BALANCE INQUIRY ERROR] [{request.user}] -- Error: {e.args}")
            return HttpResponse(
                json.dumps({'message': MSG_BALANCE_INQUIRY_ERROR}),
                status=status.HTTP_400_BAD_REQUEST
                )
        else:
            WALLET_API_LOGGER.debug(f"[response] [BALANCE INQUIRY] [{request.user}] -- {response.text}")
        if response.ok:
            resp_json = response.json()
            if resp_json["TXNSTATUS"] == '200':
                    balance = resp_json['BALANCE']
                    if total_doc_amount > balance :
                        return HttpResponse(
                            json.dumps({'message': "Insufficient funds"}),
                            status=status.HTTP_400_BAD_REQUEST
                            )
            else:
                error_message = resp_json.get('MESSAGE', None) or _("Balance inquiry failed")
                return HttpResponse(
                    json.dumps({'message': error_message}),
                    status=status.HTTP_400_BAD_REQUEST
                    )

        else:
            error_message = resp_json.get('MESSAGE', None) or _("Balance inquiry failed")
            return HttpResponse(
                    json.dumps({'message': error_message}),
                    status=status.HTTP_400_BAD_REQUEST
                    )

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests to make a disbursement for a bulk of MSISDNs
        """

        # 1. Validate the serializer's data
        serializer = DisbursementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc_obj = Doc.objects.get(id=serializer.validated_data['doc_id'])

        # 2. Validate the used pin if it is stored
        pin = serializer.validated_data['pin']
        if doc_obj.owner.root.pin and not doc_obj.owner.root.check_pin(pin):
            return HttpResponse(
                    json.dumps({'message': MSG_PIN_INVALID, 'header': 'Error occurred from your side!'}),
                    status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Retrieve the disbursement action maker (checker user)
        checker = User.objects.get(username=serializer.validated_data['user'])
        temp_response = {'BATCH_ID': '0', 'TXNSTATUS': '200'}
        vf_response = False

        # 4. Run the task to disburse any records on (vodafone, etisalat, aman, bank wallets/orange)
        BulkDisbursementThroughOneStepCashin.delay(
            doc_id=str(doc_obj.id), checker_username=str(checker.username), pin=pin
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
        DATA_LOGGER.debug(f"[response] [automatic bulk disbursement callback] [{request.user}] -- {str(request.data)}")
        total_disbursed_amount = 0
        last_doc_record_id = successfully_disbursed_obj = None
        num_of_trns = 0

        if len(request.data['transactions']) == 0:
            return JsonResponse({'message': 'Transactions are empty'}, status=status.HTTP_404_NOT_FOUND)

        for data in request.data['transactions']:
            try:
                last_doc_record_id = int(data['id'])
                # for None cases and not nullable refernce_id field
                ref_id = data.get('mpg_rrn', 'None')
                if ref_id is None:
                    ref_id = "None"
                DisbursementData.objects.select_for_update().filter(id=int(data['id'])).update(
                        is_disbursed=True if data['status'] == '0' else False,
                        reason=data.get('description', 'No Description found'),
                        reference_id=ref_id
                )

                # If data['status'] = 0, it means this record amount is disbursed successfully
                if data['status'] == '0':
                    num_of_trns = num_of_trns + 1
                    successfully_disbursed_obj = DisbursementData.objects.get(id=int(data['id']))
                    total_disbursed_amount += round(Decimal(successfully_disbursed_obj.amount), 2)
            except DisbursementData.DoesNotExist:
                return JsonResponse({}, status=status.HTTP_404_NOT_FOUND)

        if successfully_disbursed_obj is not None and successfully_disbursed_obj.doc.owner.root.has_custom_budget:
            successfully_disbursed_obj.doc.owner.root.budget.\
                update_disbursed_amount_and_current_balance(total_disbursed_amount, "vodafone", num_of_trns)
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


class CancelAmanTransactionView(APIView):

    http_method_names = ['post']

    def __init__(self):
        self.req_headers = {'Content-Type': 'application/json'}
        self.authentication_url = "https://accept.paymobsolutions.com/api/auth/tokens"
        self.api_key = get_value_from_env("ACCEPT_API_KEY")
        self.payload = {'api_key': self.api_key}
        self.void_url = "https://accept.paymob.com/api/acceptance/void_refund/void?token="


    def post(self, request, *args, **kwargs):

        if not request.is_ajax():
            return JsonResponse(data={}, status=status.HTTP_403_FORBIDDEN)

        trn_id = request.data.get('transaction_id', None)
        if not trn_id:
            return JsonResponse(data={"canceled": False, "message": "missed transaction ID"}, status=401)
        token = self.create_auth_token()
        resp = self.void_transaction(trn_id, token)


        if resp.json().get("success") == True:
            disb_trn = DisbursementData.objects.get(reference_id=trn_id)
            aman_obj = disb_trn.aman_obj.first()
            aman_obj.is_cancelled = True
            aman_obj.save()
            balance_before = disb_trn.doc.owner.root.budget.get_current_balance()
            balance_after = disb_trn.doc.owner.root.budget.return_disbursed_amount_for_cancelled_trx(disb_trn.amount)
            disb_trn.balance_before = balance_before
            disb_trn.balance_after = balance_after
            disb_trn.save()

            return JsonResponse(data={"canceled": True}, status=200)
        else:
            return JsonResponse(data={"canceled": False, "message":"request error"}, status=200)



    def create_auth_token(self):
        response = requests.post(self.authentication_url, data=json.dumps(self.payload), headers=self.req_headers)
        token = response.json().get("token")
        return token

    def void_transaction(self,trn_id, token):
        payload = {
            "transaction_id": trn_id
        }
        resp = requests.post(f"{self.void_url}{token}", data=json.dumps(payload), headers=self.req_headers)
        return resp


class OnboardMerchant(APIView):
    """
     view for onboard merchant
    """
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        """Handles POST requests to onboard new client"""

        if not request.user.is_system_admin:
            data={
                "status" : status.HTTP_403_FORBIDDEN,
                "message": "You do not have permission"
            }
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        try:
            serializer = Merchantserializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            user_name = data["username"]
            admin_email = data.get("email","")
            idms_user_id = data["idms_user_id"]
            mobile_number = data["mobile_number"]
            root, exists = self.onbordnewadmin(user_name,admin_email,idms_user_id, mobile_number)
            if exists:
                data = {
                    "status" : status.HTTP_200_OK,
                    "message": "already created"
                }
            else:
                data = {
                    "status" : status.HTTP_201_CREATED,
                    "message": "Created"
                }
            return Response(data, status=status.HTTP_201_CREATED)

        except (Exception,ValueError) as e:
            error_msg = "Process stopped during an internal error, please can you try again."
            if len(serializer.errors) > 0:
                failure_message = serializer.errors
            else:
                failure_message = error_msg
            data = {
                "status" : status.HTTP_400_BAD_REQUEST,
                "message": failure_message
            }
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

    def define_new_admin_hierarchy(self, new_user):
        """
        Generate/Define the hierarchy of the new admin user
        :param new_user: the new admin user to be created
        :return: the new admin user with its new hierarchy
        """
        maximum = max(RootUser.objects.values_list('hierarchy', flat=True), default=False)
        maximum = 0 if not maximum else maximum

        try:
            new_user.hierarchy = maximum + 1
        except TypeError:
            new_user.hierarchy = 1

        return new_user

    def onbordnewadmin(self,user_name,root_email,idms_user_id,mobile_number):
        exists = False
        root =User.objects.filter(username=user_name)

        if root.exists():
            exists = True
            return root, exists

        else:
            try:
                if root_email == "":
                    root_email=f"{user_name}_portal_admin@paymob.com"
                # create root
                root = RootUser.objects.create(
                    username=user_name,
                    email=root_email,
                    user_type=3,
                    has_password_set_on_idms=True,
                    mobile_no = mobile_number,
                    from_accept=True
                )
                # set admin hierarchy
                root = self.define_new_admin_hierarchy(root)
                # add root field when create root
                root.root = root
                root.idms_user_id = idms_user_id

                # add permissions
                root.user_permissions.add(
                    Permission.objects.get(content_type__app_label='users', codename='accept_vodafone_onboarding'),
                    Permission.objects.get(content_type__app_label='users', codename='has_disbursement')
                )
                root.save()

                superadmin=User.objects.get(username=get_from_env("ACCEPT_VODAFONE_INTERNAL_SUPERADMIN"))

                entity_dict = {
                    "user": superadmin,
                    "entity": root,
                    "agents_setup": True,
                    "fees_setup"  : True,
                    "is_normal_flow" : False,
                }
                client_dict = {
                    "creator": superadmin,
                    "client": root,
                }

                Setup.objects.create(
                    user=root, pin_setup=True, levels_setup=True,
                    maker_setup=True, checker_setup=True, category_setup=True
                )
                CallWalletsModerator.objects.create(
                    user_created=root, instant_disbursement=False, set_pin=False,
                    user_inquiry=False, balance_inquiry=False
                )

                EntitySetup.objects.create(**entity_dict)
                Client.objects.create(**client_dict)

                msg = f"New Root/Admin created with username: {root.username} by {self.request.user}"
                logging_message(ROOT_CREATE_LOGGER, "[message] [NEW ADMIN CREATED FROM ACCEPT]", self.request, msg)

                # handle budget and fees setup
                root_budget = Budget.objects.create(disburser=root, created_by=superadmin)

                FeeSetup.objects.create(budget_related=root_budget, issuer='vf',
                    fee_type='p', percentage_value=get_from_env("VF_PERCENTAGE_VALUE"))
                FeeSetup.objects.create(budget_related=root_budget, issuer='es',
                    fee_type='p', percentage_value=get_from_env("ES_PERCENTAGE_VALUE"))
                FeeSetup.objects.create(budget_related=root_budget, issuer='og',
                   fee_type='p', percentage_value=get_from_env("OG_PERCENTAGE_VALUE"))
                FeeSetup.objects.create(budget_related=root_budget, issuer='bw',
                    fee_type='p', percentage_value=get_from_env("BW_PERCENTAGE_VALUE"))
                FeeSetup.objects.create(budget_related=root_budget, issuer='am',
                    fee_type='p', percentage_value=get_from_env("AM_PERCENTAGE_VALUE"))
                FeeSetup.objects.create(budget_related=root_budget, issuer='bc',
                    fee_type='m', fixed_value=0.0,
                    percentage_value=get_from_env("Bc_PERCENTAGE_VALUE"),
                    min_value=get_from_env("BC_min_VALUE"),
                    max_value=get_from_env("BC_max_VALUE")
                )
                return root, exists

            except Exception as err:
                logging_message(
                    ROOT_CREATE_LOGGER, "[error] [error when onboarding new client]",
                    self.request, f"error :-  Error: {err.args}"
                )
                error_msg = "Process stopped during an internal error, please can you try again."
                error = {
                    "message": error_msg
                }
