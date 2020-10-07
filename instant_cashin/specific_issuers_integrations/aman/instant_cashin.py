# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal
from requests.exceptions import ConnectionError, HTTPError
import json
import logging
import requests

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from rest_framework import status
from rest_framework.response import Response

from data.utils import get_client_ip

from ...api.serializers import InstantTransactionResponseModelSerializer
from ...models import AmanTransaction
from ...utils import get_from_env


EXTERNAL_ERROR_MSG = _("Process stopped during an external error, can you try again or contact your support team.")


class AmanChannel:
    """
    Handles AMAN one-step cashin request
    """

    def __init__(self, request, transaction_object=False, amount=0.0):
        """Instantiates Aman channel object by setting ACCEPT endpoints urls"""
        self.request = request
        self.transaction = transaction_object
        self.amount = self.transaction.amount if transaction_object else amount
        self.aman_logger = logging.getLogger('aman_channel')
        self.authentication_url = "https://accept.paymobsolutions.com/api/auth/tokens"
        self.order_registration_url = "https://accept.paymobsolutions.com/api/ecommerce/orders"
        self.payment_key_url = "https://accept.paymobsolutions.com/api/acceptance/payment_keys"
        self.pay_request_url = "https://accept.paymobsolutions.com/api/acceptance/payments/pay"
        # self.merchant_notification_url = f"{self.request.get_host()}/paymob_notification_callback?hmac="

    def log_message(self, request, head, message):
        """Custom logging for aman channel"""
        user_portion = f"[{request['user']}]" if type(request) == dict else f"[{request.user}]"
        self.aman_logger.debug(_(f"{head} {user_portion} -- {message}"))

    def post(self, url, payload, sub_logging_head, headers=dict(), **kwargs):
        """Handles POST requests using requests package"""
        if headers.get('Content-Type', None) is None:
            headers.update({'Content-Type': 'application/json'})

        self.log_message(
               request=self.request, head=f"[request] [{sub_logging_head}]", message=f"Payload: {payload}, URL: {url}"
        )

        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers, **kwargs)
            response.raise_for_status()
            response_log_message = f"{response.json()}"
        except HTTPError as http_err:
            response_log_message = f"HTTP error occurred: {http_err}"
        except ConnectionError as connect_err:
            response_log_message = f"Connection establishment error: {connect_err}"
        except Exception as err:
            response_log_message = f"Other error occurred: {err}"
        else:
            return response
        finally:
            self.log_message(self.request, f"[response] [{sub_logging_head}]", response_log_message)

        raise ValidationError(_(response_log_message))

    def api_authentication(self):
        """Generate auto token from Accept"""
        payload = {
            "api_key": get_from_env("ACCEPT_API_KEY")
        }

        try:
            response = self.post(url=self.authentication_url, payload=payload, sub_logging_head="API AUTHENTICATION")
            json_response = response.json()
            token = json_response.get('token', False)
            merchant_id = json_response.get('profile', False).get('id', False)
            return Response({'api_auth_token': token, 'merchant_id': merchant_id}, status=status.HTTP_201_CREATED)
        except (HTTPError, ConnectionError, Exception):
            return Response(
                    {'message': 'Failed to generate new auth token from Accept'},
                    status=status.HTTP_424_FAILED_DEPENDENCY
            )

    def order_registration(self, api_auth_token, merchant_id, transaction_id):
        """
        Register a new order on Accept so that you can take/pay for it later using a transaction
        :param api_auth_token: Auth token generated from api_authentication response
        :param merchant_id: Merchant/User id given from api_authentication response
        :return: id of the successfully registered order
        """
        payload = {
            'auth_token': api_auth_token,
            'merchant_id': merchant_id,
            'merchant_order_id': str(transaction_id),
            'amount_cents': str(Decimal(self.amount) * 100),
            'currency': 'EGP'
        }

        try:
            response = self.post(self.order_registration_url, payload, sub_logging_head="ORDER REGISTRATION")
            json_response = response.json()
            order_id = json_response.get('id', '')
            return Response({'order_id': str(order_id)}, status=status.HTTP_201_CREATED)
        except (HTTPError, ConnectionError, Exception):
            return Response(
                    {'message': 'Failed to register new order on Accept'},
                    status=status.HTTP_424_FAILED_DEPENDENCY
            )

    def obtain_payment_key(self, api_auth_token, order_id, first_name, last_name, email, phone_number, **kwargs):
        """
        Obtain payment key token, this key will be used to authenticate your payment request
        :param api_auth_token:
        :param order_id:
        :param first_name:
        :param last_name:
        :param email:
        :param phone_number:
        :param kwargs:
        :return: token/key obtained to proceed with the payment
        """
        payload = {
            "auth_token": api_auth_token,
            "order_id": order_id,
            "amount_cents": str(Decimal(self.amount) * 100),
            "integration_id": get_from_env("INTEGRATION_ID"),
            "currency": "EGP",
            "billing_data": {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone_number": phone_number,
                "floor": "42",
                "apartment": "803",
                "street": "Ethan Land",
                "building": "8028",
                "shipping_method": "PKG",
                "postal_code": "01898",
                "city": "Cairo",
                "country": "EGY",
                "state": "Utah"
            },
            "expiration": 3600,
            "lock_order_when_paid": "false"
        }

        try:
            response = self.post(self.payment_key_url, payload, sub_logging_head="OBTAIN PAYMENT KEY")
            json_response = response.json()
            payment_token = json_response.get('token', '')
            return Response({'payment_token': payment_token}, status=status.HTTP_201_CREATED)
        except (HTTPError, ConnectionError, Exception):
            return Response(
                    {'message': f'Failed to obtain order {order_id} payment key'},
                    status=status.HTTP_424_FAILED_DEPENDENCY
            )

    def make_pay_request(self, payment_token):
        """Make payment request done to accept your order"""
        payload = {
            "source": {
                "identifier": "AGGREGATOR",
                "subtype": "AGGREGATOR"
            },
            "payment_token": payment_token
        }

        try:
            response = self.post(self.pay_request_url, payload, sub_logging_head="MAKE PAY REQUEST")
            json_response = response.json()
            bill_reference = json_response.get('data', '').get('bill_reference', '')
            trx_status = json_response.get('pending', '')
            transaction_id = json_response.get('order', '').get('merchant_order_id', '')

            if response.ok and bill_reference and trx_status:
                msg = _(f"“برجاء التوجه إلى فرع أمان. اسأل على خدمة مدفوعات أكسبت. اسخدم الكود الخاص {bill_reference} . لصرف مبلغ {self.amount} جنيه . شكراً لاختيارك مدفوعات أكسبت.“")

                if self.transaction:
                    self.transaction.mark_successful(status.HTTP_200_OK, msg)
                    AmanTransaction.objects.create(transaction=self.transaction, bill_reference=bill_reference)
                    self.request.user.root.budget.update_disbursed_amount_and_current_balance(self.amount, "aman")
                    return Response(InstantTransactionResponseModelSerializer(self.transaction).data)

                return Response({
                    "disbursement_status": _("success"),
                    "transaction_id": transaction_id,
                    "status_description": msg,
                    "status_code": str(status.HTTP_200_OK),
                    "cashing_details": {
                        "bill_reference": _(f"{bill_reference}"),
                        "paid": False
                    }
                }, status=status.HTTP_200_OK)
            else:
                if self.transaction:
                    self.transaction.mark_failed(status.HTTP_504_GATEWAY_TIMEOUT, EXTERNAL_ERROR_MSG)
                    return Response(
                            InstantTransactionResponseModelSerializer(self.transaction).data,
                            status=status.HTTP_200_OK
                    )
                return Response({
                    "disbursement_status": _("failed"),
                    "transaction_id": transaction_id,
                    "status_description": EXTERNAL_ERROR_MSG,
                    "status_code": str(status.HTTP_504_GATEWAY_TIMEOUT),
                }, status=status.HTTP_200_OK)

        except (HTTPError, ConnectionError, Exception) as err:
            self.log_message(self.request, f"[EXCEPTION - MAKE PAY REQUEST]", f"Exception: {err.args[0]}")
            return Response({'message': f'Failed to make your pay request'}, status=status.HTTP_424_FAILED_DEPENDENCY)

    @staticmethod
    def notify_merchant(payload):
        """This endpoint will be invoked every time Accept server needs to notify us about a TRANSACTION"""
        is_success = payload.get("obj", "").get("success", "")
        bill_reference = payload.get("obj", "").get("id", "")

        try:
            if is_success == "true" and bill_reference:
                AmanTransaction.objects.filter(bill_reference=bill_reference).update(is_paid=True)
                return True, ""
            raise ValueError(_(f"Transaction payment failed! is_success: {is_success}, bill_ref: {bill_reference}"))
        except (AmanTransaction.DoesNotExist, ValueError, Exception) as err:
            return False, err.args[0]
