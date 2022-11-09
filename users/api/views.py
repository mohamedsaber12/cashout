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
from .serializers import DisbursementCallBackSerializer, DisbursementSerializer,DisbursementDataSerializer, InstantTransactionSerializer
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
from .serializers import Prtaluserserializer



ROOT_CREATE_LOGGER = logging.getLogger("root_create")
CHANGE_PROFILE_LOGGER = logging.getLogger("change_fees_profile")
DATA_LOGGER = logging.getLogger("disburse")
WALLET_API_LOGGER = logging.getLogger("wallet_api")


DISBURSEMENT_ERR_RESP_DICT = {'message': _(MSG_DISBURSEMENT_ERROR), 'header': _('Error occurred, We are sorry')}
DISBURSEMENT_RUNNING_RESP_DICT = {'message': _(MSG_DISBURSEMENT_IS_RUNNING), 'header': _('Disbursed, Thanks')}



class OnboardPortalUser(APIView):
    """
     view for onboard portal user 
    """
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        """Handles POST requests to onboard new client"""

        if not request.user.is_system_admin:
                data={"status" : status.HTTP_403_FORBIDDEN,
                "message": "You do not have permission"}
                return Response(data, status=status.HTTP_400_BAD_REQUEST)
        try:
            serializer = Prtaluserserializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            user_name=data["username"]
            admin_email= data["email"]
            idms_user_id=data["idms_user_id"]
            root,data=self.onbordnewadmin(user_name,admin_email,idms_user_id)
            
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

    def onbordnewadmin(self,user_name,root_email,idms_user_id):
        
        root =User.objects.filter(username=user_name).first()
        
        if root:
            data = {
                "status" : status.HTTP_200_OK,
                "message": "user already exists"
            }
            return root,data

        else:
            try:
                client_name=user_name
                # create root
                root = RootUser.objects.create(
                username=client_name,
                email=root_email,
                user_type=3,
                has_password_set_on_idms=True,
                idms_user_id=idms_user_id,
                from_accept=True
                )
                # set admin hierarchy
                root = self.define_new_admin_hierarchy(root)
                # add root field when create root
                root.root = root
                root.save()
                # add permissions
                root.user_permissions.add(
                Permission.objects.get(content_type__app_label='users', codename='accept_vodafone_onboarding'),
                Permission.objects.get(content_type__app_label='users', codename='has_instant_disbursement')
                )
                # start create extra setup
                superadmin=User.objects.get(username=get_from_env("ACCEPT_VODAFONE_INTERNAL_SUPERADMIN"))
                entity_dict = {
                "user": superadmin,
                "entity": root,
                "agents_setup": True,
                "fees_setup": True
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
                user_created=root, disbursement=False, change_profile=False,
                set_pin=False, user_inquiry=False, balance_inquiry=False
                )
                root.user_permissions. \
                add(Permission.objects.get(content_type__app_label='users', codename='has_disbursement'))
                EntitySetup.objects.create(**entity_dict)
                Client.objects.create(**client_dict)
                # finish create extra setup
                msg = f"New Root/Admin created with username: {root.username} by {superadmin.username}"
                logging_message(ROOT_CREATE_LOGGER, "[message] [NEW ADMIN CREATED]", self.request, msg)
                # handle budget and fees setup
                root_budget = Budget.objects.create(
                disburser=root, created_by=superadmin, current_balance=0
                )
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
                data = {
                "status" : status.HTTP_201_CREATED,
                "message": "Created"
                }
                return root,data
            
            except Exception as err:
                logging_message(
                    ROOT_CREATE_LOGGER, "[error] [error when onboarding new client]",
                    self.request, f"error :-  Error: {err.args}"
                )
                error_msg = "Process stopped during an internal error, please can you try again."
                error = {
                "message": error_msg
                }
            
