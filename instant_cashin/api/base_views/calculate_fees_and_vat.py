from http.client import HTTPResponse
import json
from django.utils.translation import gettext as _
from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope, permissions
from rest_framework import status, views
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from ..mixins import(IsInstantAPICheckerUser)
from ..serializers import Costserializer
INTERNAL_ERROR_MSG = _("Process stopped during an internal error, can you try again or contact your support team.")

class Calculate_fees_and_vat_APIView(views.APIView):
    """
    Handles Calculate fees and vat request from api
    """
    permission_classes = [permissions.IsAuthenticated, TokenHasReadWriteScope, IsInstantAPICheckerUser]
    def post(self, request, *args, **kwargs):
        """Handles POST requests of the  api view"""

        serializer=Costserializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            fees, vat = request.user.root.budget.calculate_fees_and_vat_for_amount(
                    serializer.validated_data.get('amount'),serializer.validated_data.get('issuer')
            )
            return Response({"fees":str(fees),"vat":str(vat),"total_amount":str(serializer.validated_data.get('amount')+fees+vat)}, status=status.HTTP_200_OK)

        except (ValidationError, ValueError, Exception) as e:
          
            if len(serializer.errors) > 0:
                failure_message = serializer.errors
            else:
                failure_message = INTERNAL_ERROR_MSG
            return Response({
                "description_status": _("failed"), "status_description": failure_message,
                "status_code": str(status.HTTP_400_BAD_REQUEST)
            }, status=status.HTTP_400_BAD_REQUEST)