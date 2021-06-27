# import logging

# from django.http import JsonResponse
# from rest_framework.generics import GenericAPIView

# from data.models import FileData
# from payment.api.serializers import TransactionSerializer


# class TransactionCallbackAPIView(GenericAPIView):
#     serializer_class = TransactionSerializer

#     def log(self, _type: str, _from: str, _to: str, data: dict):
#         """
#         Log whatever is response or request, traceback the error
#         in case of exception not handled
#         :param type: Request or response or error
#         :param _from: from who
#         :param _to: to who
#         :param data: dictionary of post data or response data
#         :return: None
#         """
#         if _type in ('req', 'err'):
#             DATA_LOGGER = logging.getLogger("bill_payment_req")
#         elif _type == 'res':
#             DATA_LOGGER = logging.getLogger("bill_payment_res")
#         else:
#             DATA_LOGGER = logging.getLogger("bill_payment_req")
#             DATA_LOGGER.exception(f'Data to {_to} from { _from }')
#             return
#         DATA_LOGGER.debug(f'Data to {_to} from { _from }<-- \n {str(data)}')

#     def set_collection(self, data: FileData):
#         self.collection = data.user.collection

#     def post(self, request, *args, **kwargs):
#         ref = request.data.get('ref', None)
#         if ref:
#             data = FileData.objects.get(id=ref)
#             self.set_collection(data)
#             self.log('req', request.user, data.user.username, request.data)
#         else:
#             return JsonResponse(data={"message": "ref is not valid or not found"}, status=400)
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         bill_due_amount = float(data.data[self.collection.payable_amount_field])
#         paid_amount = float(serializer.validated_data['due_amount'])
#         if paid_amount < bill_due_amount:
#             full_payment = False
#             type_of_payment = 1
#         elif paid_amount > bill_due_amount:
#             full_payment = True
#             type_of_payment = 2
#         else:
#             full_payment = True
#             type_of_payment = 0
#         trx = serializer.save()
#         data.has_full_payment = full_payment
#         data.save()
#         trx.type_of_payment = type_of_payment
#         trx.save()
#         return JsonResponse({"msg": "Payment is processed"}, status=201)



