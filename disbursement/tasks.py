# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import json
import logging
from decimal import Decimal

import requests
from celery import Task

from django.utils import timezone
from rest_framework import status

from data.decorators import respects_language
from data.models import Doc
from instant_cashin.models import AmanTransaction
from instant_cashin.specific_issuers_integrations import AmanChannel
from payouts.settings.celery import app
from smpp.smpp_interface import send_sms
from users.models import User
from utilities.functions import custom_budget_logger, get_value_from_env

from .models import DisbursementData, DisbursementDocData


DISBURSE_LOGGER = logging.getLogger("disburse")


class BulkDisbursementThroughOneStepCashin(Task):
    """
    Task to disburse multiple records of one-step cashin issuers
    """

    @staticmethod
    def separate_recipients(doc_id):
        """
        :param doc_id: Id of the document being disbursed
        :return: tuple of issuers' specific recipients
        """
        recipients = DisbursementData.objects.filter(doc_id=doc_id)

        etisalat_recipients = recipients.filter(issuer='etisalat'). \
            extra(select={'msisdn': 'msisdn', 'amount': 'amount', 'txn_id': 'id'}).values('msisdn', 'amount', 'txn_id')
        orange_recipients = recipients.filter(issuer='orange'). \
            extra(select={'msisdn': 'msisdn', 'amount': 'amount', 'txn_id': 'id'}).values('msisdn', 'amount', 'txn_id')
        aman_recipients = recipients.filter(issuer='aman'). \
            extra(select={'msisdn': 'msisdn', 'amount': 'amount', 'txn_id': 'id'}).values('msisdn', 'amount', 'txn_id')

        return list(etisalat_recipients), list(orange_recipients), list(aman_recipients)

    def handle_disbursement_callback(self, recipient, callback, issuer):
        """Handle disbursement callback depending on issuer based recipients"""
        try:
            trx_callback_status = False
            if issuer == "etisalat":
                callback_json = callback.json()
                trx_callback_status = callback_json["TXNSTATUS"]
                reference_id = callback_json["TXNID"]
            elif issuer == "aman":
                if callback.status_code == status.HTTP_200_OK:
                    send_sms(f"+{str(recipient['msisdn'])[2:]}", callback.data["status_description"], "PayMob")
                    trx_callback_status = "200"
                    reference_id = callback.data["cashing_details"]["bill_reference"]
                else:
                    trx_callback_status = callback.status_code

            disbursement_data_record = DisbursementData.objects.get(id=recipient["txn_id"])
            disbursement_data_record.reference_id = reference_id
            disbursement_data_record.is_disbursed = True if trx_callback_status == "200" else False
            disbursement_data_record.reason = "SUCCESS" if trx_callback_status == "200" else trx_callback_status
            doc_obj = disbursement_data_record.doc
            disbursement_data_record.save()

            if issuer == "aman":
                AmanTransaction.objects.create(
                        transaction=disbursement_data_record,
                        bill_reference=callback.data["cashing_details"]["bill_reference"]
                )

            if trx_callback_status == "200":
                doc_obj.owner.root.budget. \
                    update_disbursed_amount_and_current_balance(disbursement_data_record.amount, issuer)
                custom_budget_logger(
                        doc_obj.owner.root.username,
                        f"Total disbursed amount: {disbursement_data_record.amount} LE",
                        doc_obj.owner.username, f", doc id: {doc_obj.id}"
                )

            return True
        except (DisbursementData.DoesNotExist, Exception):
            return False

    def disburse_for_etisalat(self, checker, superadmin, ets_recipients):
        """Disburse for etisalat specific recipients"""
        from .api.views import DisburseAPIView          # Circular import

        wallets_env_url = get_value_from_env(superadmin.vmt.vmt_environment)
        ets_pin = get_value_from_env(f"{superadmin.username}_ETISALAT_PIN")
        _, ets_agents = DisburseAPIView.prepare_agents_list(provider=checker.root, raw_pin="000000")

        for recipient in ets_recipients:
            ets_payload, ets_log_payload = superadmin.vmt.accumulate_instant_disbursement_payload(
                    ets_agents[0], recipient['msisdn'], recipient['amount'], ets_pin, 'etisalat'
            )
            ets_callback = DisburseAPIView.disburse_for_recipients(
                    wallets_env_url, ets_payload, checker.username, ets_log_payload
            )
            self.handle_disbursement_callback(recipient, ets_callback, issuer='etisalat')

    def aman_api_authentication_params(self, aman_channel_object):
        """Handle retrieving token/merchant_id from api_authentication method of aman channel"""
        api_auth_response = aman_channel_object.api_authentication()

        if api_auth_response.status_code == status.HTTP_201_CREATED:
            api_auth_token = api_auth_response.data.get("api_auth_token", "")
            merchant_id = str(api_auth_response.data.get("merchant_id", ""))

            return api_auth_token, merchant_id

    def disburse_for_aman(self, checker, ip_address, aman_recipients):
        """Disburse for aman specific recipients"""
        request = {
            "user": checker,
            "ip_address": ip_address
        }

        for recipient in aman_recipients:
            aman_object = AmanChannel(request, amount=recipient["amount"])

            try:
                api_auth_token, merchant_id = self.aman_api_authentication_params(aman_object)
                order_registration = aman_object.order_registration(api_auth_token, merchant_id, recipient["txn_id"])

                if order_registration.status_code == status.HTTP_201_CREATED:
                    api_auth_token, _ = self.aman_api_authentication_params(aman_object)
                    payment_key_params = {
                        "api_auth_token": api_auth_token,
                        "order_id": order_registration.data.get("order_id", ""),
                        "first_name": "Manual",
                        "last_name": "Patch",
                        "email": f"confirmrequest@paymob.com",
                        "phone_number": f"+{str(recipient['msisdn'])[2:]}"
                    }
                    payment_key_obtained = aman_object.obtain_payment_key(**payment_key_params)

                    if payment_key_obtained.status_code == status.HTTP_201_CREATED:
                        payment_key = payment_key_obtained.data.get("payment_token", "")
                        aman_callback = aman_object.make_pay_request(payment_key)
                        self.handle_disbursement_callback(recipient, aman_callback, issuer="aman")

            except Exception as err:
                aman_object.log_message(request, f"[GENERAL FAILURE - AMAN CHANNEL]", f"Exception: {err.args[0]}")

    def run(self, doc_id, checker_username, ip_address, *args, **kwargs):
        """
        :param doc_id: id of the document being disbursed
        :param checker_username: username of the checker who is taking the disbursement action
        :return
        """
        try:
            doc_obj = Doc.objects.get(id=doc_id)
            checker = User.objects.get(username=checker_username)
            superadmin = checker.root.client.creator
            ets_recipients, orange_recipients, aman_recipients = self.separate_recipients(doc_obj.id)

            if ets_recipients:
                self.disburse_for_etisalat(checker, superadmin, ets_recipients)
            if orange_recipients:
                pass
            if aman_recipients:
                self.disburse_for_aman(checker, ip_address, aman_recipients)

            if ets_recipients or orange_recipients or aman_recipients:
                DisbursementDocData.objects.filter(doc=doc_obj).update(has_callback=True)

        except (Doc.DoesNotExist, User.DoesNotExist, Exception) as err:
            DISBURSE_LOGGER.\
                debug(f"[message] [BULK DISBURSEMENT ERROR - ONE STEP TASK] [{checker_username}] -- {err.args}")
            return False

        return True


BulkDisbursementThroughOneStepCashin = app.register_task(BulkDisbursementThroughOneStepCashin())


@app.task()
@respects_language
def check_for_late_disbursement_callback(**kwargs):
    """Background task for getting the bulk disbursement callback"""
    day_ago = timezone.now() - datetime.timedelta(int(1))
    disbursement_doc_data = DisbursementDocData.objects.\
        filter(updated_at__gte=day_ago, doc_status=DisbursementDocData.DISBURSED_SUCCESSFULLY, has_callback=False)

    if disbursement_doc_data.count() < 1:
        return False

    for disbursement_doc in disbursement_doc_data:
        try:
            superadmin = disbursement_doc.doc.owner.root.super_admin
            payload = superadmin.vmt.\
                accumulate_disbursement_or_change_profile_callback_inquiry_payload(disbursement_doc.txn_id)
            DISBURSE_LOGGER.debug(f"[request] [bulk disbursement callback inquiry] [celery_task] -- {payload}")
            response = requests.post(get_value_from_env(superadmin.vmt.vmt_environment), json=payload, verify=False)
        except Exception as e:
            DISBURSE_LOGGER.debug(f"[message] [bulk disbursement callback inquiry error] [celery_task] -- {e.args}")
            continue
        else:
            DISBURSE_LOGGER.debug(f"[response] [bulk disbursement callback inquiry] [celery_task] -- {response.text}")

        doc_transactions = json.loads(response.text)["TRANSACTIONS"]
        total_disbursed_amount = 0

        if len(doc_transactions) == 0:
            continue
        else:
            for disb_record in doc_transactions:
                DisbursementData.objects.select_for_update().filter(id=int(disb_record['id'])).update(
                        is_disbursed=True if disb_record['status'] == '0' else False,
                        reason=disb_record.get('description', 'No Description found'),
                        reference_id=disb_record.get('mpg_rrn', 'None')
                )

                # If disb_record['status'] = 0, it means this record amount is disbursed successfully
                if disbursement_doc.doc.owner.root.has_custom_budget and disb_record['status'] == '0':
                    total_disbursed_amount += Decimal(DisbursementData.objects.get(id=disb_record['id']).amount)

            if disbursement_doc.doc.owner.root.has_custom_budget and total_disbursed_amount > 0:
                disbursement_doc.doc.owner.root.budget.\
                    update_disbursed_amount_and_current_balance(total_disbursed_amount, "vodafone")
                custom_budget_logger(
                        disbursement_doc.doc.owner.root, f"Total disbursed amount: {total_disbursed_amount} LE",
                        "celery_task", f" -- doc id: {disbursement_doc.doc.id}"
                )

            disbursement_doc.has_callback = True
            disbursement_doc.save()
