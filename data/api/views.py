import logging
from django.db.models import Q
from django.http import JsonResponse
from rest_framework import status
from rest_framework.generics import GenericAPIView

from data.api.serializers import BillInquiryRequestSerializer
from data.models import FileData

from datetime import datetime


class BillInquiryAPIView(GenericAPIView):
    """
    Api for data retrieval based on the bill references
    with Token Authentication
    """
    serializer_class = BillInquiryRequestSerializer

    def log(self, _flag: str, _type: str, _from: str, _to: str, data: dict):
        """
        Log whatever is response or request, traceback the error
        in case of exception not handled
        :param _flag: all caps operation indicator flag
        :param _type: Request or response or error
        :param _from: from who
        :param _to: to who
        :param data: dictionary of post data or response data
        :return: None
        """
        if _type in ('req', 'err'):
            DATA_LOGGER = logging.getLogger("bill_inquiry_req")
        elif _type == 'res':
            DATA_LOGGER = logging.getLogger("bill_inquiry_res")
        else:
            DATA_LOGGER = logging.getLogger("bill_inquiry_req")
            DATA_LOGGER.debug(f"\n{datetime.now().strftime('%d/%m/%Y %H:%M')} ----> UNHANDLED_EXCEPTION\n\tData to SUPER: {_to}, from ADMIN: {_from}")
            return
        DATA_LOGGER.debug(f"\n{datetime.now().strftime('%d/%m/%Y %H:%M')} ----> {_flag}\n\tData to SUPER: {_to}, from ADMIN: {_from}\n\t{str(data)}")

    def post(self, request, *args, **kwargs):
        self.log("BILL_INQUIRY_REQUEST", "req", request.user.username, request.data.get("aggregator", "N/A"), request.data)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.biller = request.user
        self.collection = self.biller.collection_data
        try:
            response = self.serialize_response_data(serializer.validated_data)
        except Exception as e:
            self.log("BILL_INQUIRY_ERROR", "err", request.user.username, request.data("aggregator", "N/A"), {})
            return JsonResponse({"msg": "Error Occurred"}, status=status.HTTP_417_EXPECTATION_FAILED)
        self.log("BILL_INQUIRY_RESPONSE", "res", request.user.username, serializer.validated_data["aggregator"], response.content)
        return response

    def get_bill(self, data: dict):
        """
        :param data: Serialized data that has been submitted to post request.
        :param aggregator: UserAccount instance that submitted the request.
        :param category: The required FileCategory instance.
        :param biller: UserAccount instance that relates to aggregator.
        :return: QuerySet, otherwise JsonResponse.
        """
        try:
            if self.collection.unique_field2:
                file_data = FileData.objects.filter(
                    Q(user=self.biller) &
                    Q(has_full_payment=False) &
                    Q(**{f'data__{self.collection.unique_field}': data['bill_reference']}) &
                    Q(**{f'data__{self.collection.unique_field2}': data['bill_reference2']})
                )
            else:
                file_data = FileData.objects.filter(
                    Q(**{f'data__{self.collection.unique_field}': data['bill_reference']}) &
                    Q(user=self.biller) &
                    Q(has_full_payment=False)
                )

            return file_data.first()
        except KeyError:
            return JsonResponse(
                {'message': 'Bill Reference is not found', 'code': '2404'},
                status=status.HTTP_404_NOT_FOUND
            )

    def serialize_response_data(self, post_data):
        """
        Chooses the proper serializer based on return_list paramater.
        :param qurey: A QuerySet of FileData.
        :param post_data: A Dict of submitted data.
        :param request: HTTP request instance.
        :return: JSON RESPONSE.
        """
        file_data = self.get_bill(post_data)
        if isinstance(file_data, FileData):
            returned_data = {
                'ref': file_data.id,
                'code': '0001'
            }
            returned_data.update(file_data.data)
            return JsonResponse(returned_data, status=status.HTTP_200_OK)

        elif isinstance(file_data, JsonResponse):
            return file_data
        else:
            return JsonResponse({"msg": "no data supplied"}, status=status.HTTP_404_NOT_FOUND)
