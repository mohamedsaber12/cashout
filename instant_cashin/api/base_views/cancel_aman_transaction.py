# -*- coding: utf-8 -*-

from django.core.exceptions import ImproperlyConfigured

from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope, permissions
from rest_framework import views, status
from ..mixins import IsInstantAPICheckerUser
from ..serializers import CancelAmanTransactionSerializer
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from ...models import InstantTransaction
from instant_cashin.api.serializers import InstantTransactionResponseModelSerializer
import requests
import json
from utilities.functions import get_value_from_env



class CancelAmanTransactionAPIView(views.APIView):
    """
    Cancel Aman transaction API View
    """
    
    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope, IsInstantAPICheckerUser]
    
    def __init__(self):
        self.req_headers = {'Content-Type': 'application/json'}
        self.authentication_url = "https://accept.paymobsolutions.com/api/auth/tokens"
        self.api_key = get_value_from_env("ACCEPT_API_KEY")
        self.payload = {'api_key': self.api_key}
        self.void_url = "https://accept.paymob.com/api/acceptance/void_refund/void?token="
        
    def create_auth_token(self):
        response = requests.post(self.authentication_url, data=json.dumps(self.payload), headers=self.req_headers)
        token = response.json().get("token")
        return token
    
    def void_transaction(self, trn_id, token):
        payload = {
            "transaction_id": trn_id
        }
        resp = requests.post(f"{self.void_url}{token}", data=json.dumps(payload), headers=self.req_headers)
        return resp

    def post(self, request, *args, **kwargs):
        """
        Handles POST HTTP requests
        """
        serializer = CancelAmanTransactionSerializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            trans = InstantTransaction.objects.filter(from_user=request.user, uid=serializer.validated_data['transaction_id'])
            if not trans:
                return Response({"transaction_id": "Not found"}, status=status.HTTP_404_NOT_FOUND)
            token = self.create_auth_token()
            trans = trans.first()
            resp = self.void_transaction(trans.reference_id, token)        
            
            
            if resp.json().get("success") == True:
                aman_obj = trans.aman_obj.first()
                aman_obj.is_cancelled = True
                aman_obj.save()
                balance_before = request.user.root.budget.get_current_balance()
                balance_after = request.user.root.budget.return_disbursed_amount_for_cancelled_trx(trans.amount)
                trans.refresh_from_db()
                trans.balance_before = balance_before
                trans.balance_after = balance_after
                trans.save()
                resp_data = InstantTransactionResponseModelSerializer(trans)
                return Response(resp_data.data)
            else:
                return Response({"is_canelled": False}, status=status.HTTP_400_BAD_REQUEST)
            
        except (ValidationError, ValueError, Exception) as e:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)