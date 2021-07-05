from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.reverse import reverse as api_reverse
from urllib.parse import urlencode
from oauth2_provider.models import Application

from users.tests.factories import InstantAPICheckerFactory
from utilities.models import Budget
from instant_cashin.models import AmanTransaction, InstantTransaction

class CurrentRequest(object):
    def __init__(self, user=None):
        self.user=user


class AmanTransactionCallbackHandlerAPIViewTests(APITestCase):

    def setUp(self):
        super().setUp()
        self.data = {
            "obj": {
                "id": 6918187,
                "pending": False,
                "amount_cents": 48006,
                "success": False,
                "is_auth": False,
                "is_capture": False,
                "is_standalone_payment": True,
                "is_voided": True,
                "is_refunded": False,
                "is_3d_secure": False,
                "integration_id": 16082,
                "profile_id": 9201,
                "has_parent_transaction": False,
                "order": {
                    "id": 10000747,
                    "created_at": "2021-03-29T14:52:59.659251",
                    "delivery_needed": False,
                    "merchant": {
                        "id": 9201,
                        "created_at": "2020-04-05T19:20:52.543724",
                        "phones": [
                            "01092737975"
                        ],
                        "company_emails": [
                            "mohamedmamdouh@paymobsolutions.com"
                        ],
                        "company_name": "PayMob",
                        "state": "",
                        "country": "EGY",
                        "city": "cairo",
                        "postal_code": "",
                        "street": ""
                    },
                    "collector": None,
                    "amount_cents": 48006,
                    "shipping_data": {
                        "id": 6388719,
                        "first_name": "Manual",
                        "last_name": "Patch",
                        "street": "Ethan Land",
                        "building": "8028",
                        "floor": "42",
                        "apartment": "803",
                        "city": "Cairo",
                        "state": "Utah",
                        "country": "EGY",
                        "email": "noreply@paymob.com",
                        "phone_number": "+201264768888",
                        "postal_code": "01898",
                        "extra_description": "",
                        "shipping_method": "UNK",
                        "order_id": 10000747,
                        "order": 10000747
                    },
                    "shipping_details": None,
                    "currency": "EGP",
                    "is_payment_locked": False,
                    "is_return": False,
                    "is_cancel": False,
                    "is_returned": False,
                    "is_canceled": False,
                    "merchant_order_id": "1187",
                    "wallet_notification": None,
                    "paid_amount_cents": 0,
                    "notify_user_with_email": False,
                    "items": [],
                    "order_url": "https://accept.paymobsolutions.com/i/K0cv",
                    "commission_fees": 0,
                    "delivery_fees_cents": 0,
                    "delivery_vat_cents": 0,
                    "payment_method": "tbc",
                    "merchant_staff_tag": None,
                    "api_source": "OTHER",
                    "pickup_data": None,
                    "delivery_status": [],
                    "data": {}
                },
                "created_at": "2021-03-29T14:53:01.494402",
                "transaction_processed_callback_responses": [],
                "currency": "EGP",
                "source_data": {
                    "sub_type": "AGGREGATOR",
                    "pan": "",
                    "type": "aggregator"
                },
                "api_source": "OTHER",
                "terminal_id": None,
                "is_void": False,
                "is_refund": False,
                "data": {
                    "biller": None,
                    "ref": None,
                    "cashout_amount": None,
                    "from_user": None,
                    "due_amount": 48006,
                    "gateway_integration_pk": 16082,
                    "rrn": None,
                    "otp": "",
                    "klass": "CAGGPayment",
                    "paid_through": "",
                    "amount": None,
                    "agg_terminal": None,
                    "txn_response_code": "05",
                    "message": "Pending Payment",
                    "bill_reference": 6918187
                },
                "is_hidden": False,
                "payment_key_claims": {
                    "amount_cents": 48006,
                    "pmk_ip": "41.36.166.131",
                    "order_id": 10000747,
                    "lock_order_when_paid": False,
                    "user_id": 11242,
                    "billing_data": {
                        "apartment": "803",
                        "extra_description": "NA",
                        "phone_number": "+201264768888",
                        "city": "Cairo",
                        "postal_code": "01898",
                        "first_name": "Manual",
                        "last_name": "Patch",
                        "email": "noreply@paymob.com",
                        "state": "Utah",
                        "floor": "42",
                        "street": "Ethan Land",
                        "building": "8028",
                        "country": "EGY"
                    },
                    "integration_id": 16082,
                    "currency": "EGP",
                    "exp": 1617025980
                },
                "error_occured": False,
                "is_live": False,
                "other_endpoint_reference": None,
                "refunded_amount_cents": 0,
                "source_id": -1,
                "is_captured": False,
                "captured_amount": 0,
                "merchant_staff_tag": None,
                "owner": 11242,
                "parent_transaction": None
            },
            "type": "TRANSACTION"
        }

    # test calculated hmac not equal received hmac
    def test_calculated_hmac_not_equal_received_hmac(self):
        url = api_reverse("instant_api:aman_trx_callback")
        response = self.client.post(url, self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    #  test aman transaction not found
    def test_aman_transaction_not_found(self):
        hmac = "ce1773ea8aea02f878e4a996e48c256bf17f363a5d28ad0ceb3655e5f35e16512ca6399c28d25a28481da3a1e65ff52f4cff7d95995d3154b2e2f246e79f5cb7"
        url = api_reverse("instant_api:aman_trx_callback")
        response = self.client.post('%s?hmac=%s' % (url, hmac), self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    #  test aman transaction updated successfully
    def test_aman_transaction_updated_successfully(self):
        self.data["obj"]["success"] = True
        self.instant_trx = InstantTransaction()
        self.instant_trx.save()
        self.aman_trx_obj = AmanTransaction(transaction=self.instant_trx, bill_reference=6918187)
        self.aman_trx_obj.save()
        hmac = "53ed9c701eaa97ac909e19e0736fc03c5aa652ee5e24d94d7c1c701c1df3bb2c3bf6f7583a72d86883201e3f501ecbefa5a4ac7cbc387e89970dd937ffeee724"
        url = api_reverse("instant_api:aman_trx_callback")
        response = self.client.post('%s?hmac=%s' % (url, hmac), self.data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class BudgetInquiryAPIViewTests(APITestCase):
    def setUp(self):
        super().setUp()
        # create api checker
        self.api_checker = InstantAPICheckerFactory()
        # create auth data
        Application.objects.create(
            client_type=Application.CLIENT_CONFIDENTIAL, authorization_grant_type=Application.GRANT_PASSWORD,
            name=f"{self.api_checker.username} OAuth App", user=self.api_checker
        )
        # set password for api checker
        self.api_checker.set_password('fiA#EmkjLBh9VSXy6XvFKxnR9jXt')
        self.api_checker.save()
        # get client_secret and client_id
        auth_data = Application.objects.get(user=self.api_checker)
        # get auth_token
        url = api_reverse("users:oauth2_token")
        data = urlencode({
            "client_id": auth_data.client_id,
            "client_secret": auth_data.client_secret,
            "username": self.api_checker.username,
            "password": "fiA#EmkjLBh9VSXy6XvFKxnR9jXt",
            "grant_type": "password"
        })
        response = self.client.post(url, data, content_type="application/x-www-form-urlencoded")
        self.auth_token = response.json()['access_token']



