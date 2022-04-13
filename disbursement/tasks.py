# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random
import datetime
import logging
from decimal import Decimal

import requests
from celery import Task

from django.db.models import Q
from django.utils import timezone
from rest_framework import status

from data.decorators import respects_language
from data.models import Doc
from data.tasks import handle_change_profile_callback
from instant_cashin.models import AmanTransaction
from instant_cashin.models.instant_transactions import InstantTransaction
from instant_cashin.specific_issuers_integrations import AmanChannel, BankTransactionsChannel
from instant_cashin.utils import get_from_env
from payouts.settings.celery import app
from smpp.smpp_interface import send_sms
from users.models import User
from utilities.functions import custom_budget_logger, get_value_from_env

from .models import DisbursementData, DisbursementDocData, BankTransaction

CH_PROFILE_LOGGER = logging.getLogger("change_fees_profile")
DISBURSE_LOGGER = logging.getLogger("disburse")
ETISALAT_UNKNWON_INQ = logging.getLogger("etisalat_inq_by_ref")
VODAFONE_UNKNWON_INQ = logging.getLogger("vodafone_inq_by_ref")


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

        vf_recipients = recipients.filter(issuer__in=['vodafone', 'default']). \
            extra(select={'msisdn': 'msisdn', 'amount': 'amount', 'txn_id': 'id', 'uid': 'uid'}). \
            values('msisdn', 'amount', 'txn_id', 'uid')
        etisalat_recipients = recipients.filter(issuer='etisalat'). \
            extra(select={'msisdn': 'msisdn', 'amount': 'amount', 'txn_id': 'id', 'uid': 'uid'}). \
            values('msisdn', 'amount', 'txn_id', 'uid')
        aman_recipients = recipients.filter(issuer='aman'). \
            extra(select={'msisdn': 'msisdn', 'amount': 'amount', 'txn_id': 'id', 'uid': 'uid'}). \
            values('msisdn', 'amount', 'txn_id', 'uid')

        return vf_recipients, list(etisalat_recipients), list(aman_recipients)

    def handle_disbursement_callback(self, recipient, callback, issuer):
        """Handle disbursement callback depending on issuer based recipients"""
        try:
            trx_callback_status = status.HTTP_424_FAILED_DEPENDENCY
            reference_id = recipient["txn_id"]

            if issuer == 'vodafone':
                callback_json = callback.json()
                trx_callback_status = callback_json["TXNSTATUS"]
                reference_id = callback_json["TXNID"]
                trx_callback_msg = callback_json["MESSAGE"]
            elif issuer == "etisalat":
                callback_json = callback.json()
                trx_callback_status = callback_json["TXNSTATUS"]
                reference_id = callback_json["TXNID"]
                trx_callback_msg = callback_json["MESSAGE"]
                # ToDo: After adding status_code & status_description fields to DisbursementData model
                # trx_callback_status_code = callback_json["TXNSTATUS"]
                # trx_callback_status_description = callback_json["MESSAGE"]
            elif issuer == "aman":
                if callback and callback.status_code == status.HTTP_200_OK:
                    trx_callback_status = "200"
                    trx_callback_msg = callback.data["status_description"]
                    send_sms(f"+{str(recipient['msisdn'])[2:]}", trx_callback_msg, "PayMob")
                    reference_id = callback.data["cashing_details"]["bill_reference"]

            disbursement_data_record = DisbursementData.objects.get(id=recipient["txn_id"])
            disbursement_data_record.reference_id = reference_id
            doc_obj = disbursement_data_record.doc

            if trx_callback_status == "200":
                disbursement_data_record.is_disbursed = True
                disbursement_data_record.reason = trx_callback_msg
                if doc_obj.owner.root.has_custom_budget:
                    doc_obj.owner.root.budget.update_disbursed_amount_and_current_balance(
                        disbursement_data_record.amount, issuer
                    )
            else:
                disbursement_data_record.is_disbursed = False
                if not trx_callback_status in ["501", "-1"]:
                    disbursement_data_record.reason = trx_callback_status
            disbursement_data_record.disbursed_date=datetime.datetime.now()
            disbursement_data_record.save()

            if issuer == "aman":
                AmanTransaction.objects.create(transaction=disbursement_data_record, bill_reference=reference_id)

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
                random.choice(ets_agents), recipient['msisdn'], recipient['amount'],
                ets_pin, 'etisalat', recipient['uid']
            )
            ets_callback = DisburseAPIView.disburse_for_recipients(
                wallets_env_url, ets_payload, checker.username, ets_log_payload
            )
            self.handle_disbursement_callback(recipient, ets_callback, issuer='etisalat')

    def disburse_for_vodafone(self, checker, superadmin, vf_recipients, vf_pin):
        """Disburse for vodafone specific recipients"""
        from .api.views import DisburseAPIView          # Circular import

        wallets_env_url = get_value_from_env(superadmin.vmt.vmt_environment)
        if not ( checker.is_vodafone_default_onboarding or checker.is_banks_standard_model_onboaring):
            vf_pin = get_value_from_env(f"{superadmin.username}_VODAFONE_PIN")
        vf_agents, _ = DisburseAPIView.prepare_agents_list(provider=checker.root, raw_pin=vf_pin)
        smsc_sender_name = checker.root.client.smsc_sender_name

        for recipient in vf_recipients:
            vf_payload, vf_log_payload = superadmin.vmt.accumulate_instant_disbursement_payload(
                random.choice(vf_agents)['MSISDN'], recipient['msisdn'], recipient['amount'],
                vf_pin, 'vodafone', recipient['uid'], smsc_sender_name
            )
            vf_callback = DisburseAPIView.disburse_for_recipients(
                wallets_env_url, vf_payload, checker.username, vf_log_payload, txn_id=recipient["txn_id"]
            )
            self.handle_disbursement_callback(recipient, vf_callback, issuer='vodafone')

    def aman_api_authentication_params(self, aman_channel_object):
        """Handle retrieving token/merchant_id from api_authentication method of aman channel"""
        api_auth_response = aman_channel_object.api_authentication()
        api_auth_token = merchant_id = None

        if api_auth_response.status_code == status.HTTP_201_CREATED:
            api_auth_token = api_auth_response.data.get("api_auth_token", "")
            merchant_id = str(api_auth_response.data.get("merchant_id", ""))

        return api_auth_token, merchant_id

    def disburse_for_aman(self, checker, aman_recipients):
        """Disburse for aman specific recipients"""
        request = { "user": checker }

        for recipient in aman_recipients:
            aman_object = AmanChannel(request, amount=Decimal(str(recipient["amount"])))

            try:
                # 1. Generate new auth token from Accept
                api_auth_token, merchant_id = self.aman_api_authentication_params(aman_object)

                # 2. Register the order at Accept
                order_registration = aman_object.order_registration(api_auth_token, merchant_id, recipient["txn_id"])

                if order_registration.status_code == status.HTTP_201_CREATED:
                    api_auth_token, _ = self.aman_api_authentication_params(aman_object)
                    payment_key_params = {
                        "api_auth_token": api_auth_token,
                        "order_id": order_registration.data.get("order_id", ""),
                        "first_name": "Manual",
                        "last_name": "Patch",
                        "email": f"noreply@paymob.com",
                        "phone_number": f"+{str(recipient['msisdn'])[2:]}"
                    }

                    # 3. Obtain payment key
                    payment_key_obtained = aman_object.obtain_payment_key(**payment_key_params)

                    if payment_key_obtained.status_code == status.HTTP_201_CREATED:
                        payment_key = payment_key_obtained.data.get("payment_token", "")
                        aman_callback = aman_object.make_pay_request(payment_key)
                        self.handle_disbursement_callback(recipient, aman_callback, issuer="aman")

            except Exception as err:
                aman_object.log_message(request, f"[general failure - aman bulk channel]", f"Exception: {err.args[0]}")
                self.handle_disbursement_callback(recipient, False, issuer="aman")

    def create_bank_transaction_from_instant_transaction(self, checker, record):
        """Create a bank transaction out of the passed record data/instant transaction"""

        transaction_dict = {
            "currency": "EGP",
            "debtor_address_1": "EG",
            "creditor_address_1": "EG",
            "creditor_bank": "MIDG",
            "category_code": "MOBI",
            "purpose": "CASH",
            "corporate_code": get_from_env("ACH_CORPORATE_CODE"),
            "debtor_account": get_from_env("ACH_DEBTOR_ACCOUNT"),
            "user_created": checker,
            "creditor_account_number": record.anon_recipient,
            "amount": record.amount,
            "creditor_name": record.recipient_name,
            "end_to_end": record.uid,
            "disbursed_date": record.disbursed_date
        }
        return BankTransaction.objects.create(**transaction_dict)

    def disburse_for_bank_docs(self, doc, checker):
        """
        :param doc: the document being disbursed
        :param checker: the checker user who have taken the disbursement action
        :return
        """
        if doc.is_bank_wallet:
            bank_wallets_transactions = doc.bank_wallets_transactions.all()

            for instant_trx_obj in bank_wallets_transactions:
                try:
                    instant_trx_obj.disbursed_date = timezone.now()
                    instant_trx_obj.save()
                    bank_trx_obj = self.create_bank_transaction_from_instant_transaction(checker, instant_trx_obj)
                    BankTransactionsChannel.send_transaction(bank_trx_obj, instant_trx_obj)
                except:
                    pass
        else:
            bank_cards_transactions = doc.bank_cards_transactions.all()

            for bank_trx_obj in bank_cards_transactions:
                try:
                    bank_trx_obj.disbursed_date = timezone.now()
                    bank_trx_obj.save()
                    BankTransactionsChannel.send_transaction(bank_trx_obj, False)
                except:
                    pass

    def run(self, doc_id, checker_username, pin, *args, **kwargs):
        """
        :param doc_id: id of the document being disbursed
        :param checker_username: username of the checker who is taking the disbursement action
        :return
        """
        try:
            doc_obj = Doc.objects.get(id=doc_id)
            checker = User.objects.get(username=checker_username)
            superadmin = checker.root.client.creator

            # 1. Handle doc of type E-wallets
            if doc_obj.is_e_wallet:
                vf_recipients, ets_recipients, aman_recipients = self.separate_recipients(doc_obj.id)
                if ets_recipients:
                    self.disburse_for_etisalat(checker, superadmin, ets_recipients)
                if aman_recipients:
                    self.disburse_for_aman(checker, aman_recipients)

                if vf_recipients.count() == 0 and (ets_recipients or aman_recipients):
                    DisbursementDocData.objects.filter(doc=doc_obj).update(has_callback=True)

                # handle disbursement for vodafone
                if vf_recipients:
                    self.disburse_for_vodafone(checker, superadmin, vf_recipients, pin)
                    DisbursementDocData.objects.filter(doc=doc_obj).update(has_callback=True)

            # 2. Handle doc of type bank wallets/cards
            elif doc_obj.is_bank_wallet or doc_obj.is_bank_card:
                self.disburse_for_bank_docs(doc=doc_obj, checker=checker)
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
    """Background task for asking for the late bulk disbursement callback"""
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

        doc_transactions = response.json().get("TRANSACTIONS", '')
        total_disbursed_amount = 0

        if len(doc_transactions) == 0:
            continue
        else:
            for disb_record in doc_transactions:
                ref_id = disb_record.get('mpg_rrn', "None")
                if ref_id is None:
                    ref_id = "None"
                DisbursementData.objects.select_for_update().filter(id=int(disb_record['id'])).update(
                        is_disbursed=True if disb_record['status'] == '0' else False,
                        reason=disb_record.get('description', 'No Description found'),
                        reference_id=ref_id
                )

                # If disb_record['status'] = 0, it means this record amount is disbursed successfully
                if disbursement_doc.doc.owner.root.has_custom_budget and disb_record['status'] == '0':
                    total_disbursed_amount += round(
                            Decimal(DisbursementData.objects.get(id=disb_record['id']).amount), 2
                    )

            if disbursement_doc.doc.owner.root.has_custom_budget and total_disbursed_amount > 0:
                disbursement_doc.doc.owner.root.budget.\
                    update_disbursed_amount_and_current_balance(total_disbursed_amount, "vodafone")
                custom_budget_logger(
                        disbursement_doc.doc.owner.root, f"Total disbursed amount: {total_disbursed_amount} LE",
                        "celery_task", f" -- doc id: {disbursement_doc.doc.id}"
                )

            disbursement_doc.has_callback = True
            disbursement_doc.save()

    return True


@app.task()
@respects_language
def check_for_late_change_profile_callback(**kwargs):
    """Background task for asking for the late change profile callback"""
    day_ago = timezone.now() - datetime.timedelta(int(1))
    disbursement_doc_data = DisbursementDocData.objects.filter(
            doc__created_at__gte=day_ago, doc__has_change_profile_callback=False,
            doc_status=DisbursementDocData.UPLOADED_SUCCESSFULLY
    ).filter(~Q(doc__txn_id=None))

    if disbursement_doc_data.count() < 1:
        return False

    for disbursement_doc in disbursement_doc_data:
        try:
            superadmin = disbursement_doc.doc.owner.root.super_admin
            payload = superadmin.vmt.\
                accumulate_disbursement_or_change_profile_callback_inquiry_payload(disbursement_doc.doc.txn_id)
            CH_PROFILE_LOGGER.debug(f"[request] [change profile callback inquiry] [celery_task] -- {payload}")
            response = requests.post(get_value_from_env(superadmin.vmt.vmt_environment), json=payload, verify=False)
        except Exception as e:
            CH_PROFILE_LOGGER.debug(f"[message] [change profile callback inquiry error] [celery_task] -- {e.args}")
            continue
        else:
            CH_PROFILE_LOGGER.debug(f"[response] [change profile callback inquiry] [celery_task] -- {response.text}")

        transactions = response.json().get("TRANSACTIONS", '')

        if len(transactions) == 0:
            continue
        else:
            refined_transactions_list = []
            for record in transactions:
                record_as_list = [record['MSISDN'], record['TXNSTATUS'], record['MESSAGE']]
                refined_transactions_list.append(record_as_list)
            handle_change_profile_callback.delay(disbursement_doc.doc.id, refined_transactions_list)

    return True


@app.task()
@respects_language
def check_for_etisalat_unknown_transactions(**kwargs):
    """Background task for asking for the unknown etisalat transactions"""
    unkown_trns = InstantTransaction.objects.filter(
        status__in=["U", "P"],
        issuer_type__exact="E"
    )

    for unkown_trn in unkown_trns:
        super_admin = unkown_trn.from_user.root.super_admin
        url = get_value_from_env(super_admin.vmt.vmt_environment)
        payload = super_admin.vmt.accumulate_inquiry_for_etisalat_by_ref_id(
            str(unkown_trn.uid))
        ETISALAT_UNKNWON_INQ.debug(f"[request] [ETISALAT UNKNWON TRX INQ] [celery_task] -- {payload}")
        resp = requests.post(url, json=payload, verify=False)
        resp_data = resp.json()
        ETISALAT_UNKNWON_INQ.debug(f"[response] [ETISALAT UNKNWON TRX INQ] [celery_task] -- {resp_data}")
        if resp_data.get("DATA"):
            if resp_data.get("DATA").get("TXNSTATUS"):
                if resp_data.get("DATA").get("TXNSTATUS") == "FAILED":
                    unkown_trn.status = 'F'
                    unkown_trn.save()
                elif resp_data.get("DATA").get("TXNSTATUS") == "SUCCESSFUL":
                    unkown_trn.status = 'S'
                    unkown_trn.transaction_status_code = '200'
                    unkown_trn.transaction_status_description = 'تم إيداع المبلغ بنجاح'
                    unkown_trn.save()
                    unkown_trn.from_user.root.budget.update_disbursed_amount_and_current_balance(
                            unkown_trn.amount, 'etisalat')


@app.task()
@respects_language
def check_for_etisalat_and_vodafone_unknown_transactions(**kwargs):
    """Background task for asking for the unknown etisalat and vodafone transactions"""
    unkown_e_trns = InstantTransaction.objects.filter(
        status__in=["U", "P"],
        issuer_type__exact="E"
    )

    for unkown_e_trn in unkown_e_trns:
        super_admin = unkown_e_trn.from_user.root.super_admin
        url = get_value_from_env(super_admin.vmt.vmt_environment)
        payload = super_admin.vmt.accumulate_inquiry_for_etisalat_by_ref_id(
            str(unkown_e_trn.uid))
        ETISALAT_UNKNWON_INQ.debug(f"[request] [ETISALAT UNKNWON TRX INQ] [celery_task] -- {payload}")
        resp = requests.post(url, json=payload, verify=False)
        resp_data = resp.json()
        ETISALAT_UNKNWON_INQ.debug(f"[response] [ETISALAT UNKNWON TRX INQ] [celery_task] -- {resp_data}")
        if resp_data.get("DATA"):
            if resp_data.get("DATA").get("TXNSTATUS"):
                if resp_data.get("DATA").get("TXNSTATUS") == "FAILED":
                    unkown_e_trn.status = 'F'
                    unkown_e_trn.save()
                elif resp_data.get("DATA").get("TXNSTATUS") == "SUCCESSFUL":
                    unkown_e_trn.status = 'S'
                    unkown_e_trn.transaction_status_code = '200'
                    unkown_e_trn.transaction_status_description = 'تم إيداع المبلغ بنجاح'
                    unkown_e_trn.save()
                    unkown_e_trn.from_user.root.budget.update_disbursed_amount_and_current_balance(
                            unkown_e_trn.amount, 'etisalat')

    unkown_v_trns = InstantTransaction.objects.filter(
        status__in=["U", "P"],
        issuer_type__exact="V"
    )
    for unkown_v_trn in unkown_v_trns:
        super_admin = unkown_v_trn.from_user.root.super_admin
        url = get_value_from_env(super_admin.vmt.vmt_environment)
        payload = super_admin.vmt.accumulate_inquiry_for_vodafone_by_ref_id(
            str(unkown_v_trn.uid))
        VODAFONE_UNKNWON_INQ.debug(f"[request] [VODAFONE UNKNWON TRX INQ] [celery_task] -- {payload}")
        resp = requests.post(url, json=payload, verify=False)
        resp_data = resp.json()
        VODAFONE_UNKNWON_INQ.debug(f"[response] [VODAFONE UNKNWON TRX INQ] [celery_task] -- {resp_data}")
        if resp_data.get("DATA"):
            if resp_data.get("DATA").get("TXNSTATUS"):
                if resp_data.get("DATA").get("TXNSTATUS") == "FAILED":
                    unkown_v_trn.status = 'F'
                    unkown_v_trn.save()
                elif resp_data.get("DATA").get("TXNSTATUS") == "SUCCESSFUL":
                    unkown_v_trn.status = 'S'
                    unkown_v_trn.transaction_status_code = '200'
                    unkown_v_trn.transaction_status_description = 'تم إيداع المبلغ بنجاح'
                    unkown_v_trn.save()
                    unkown_v_trn.from_user.root.budget.update_disbursed_amount_and_current_balance(
                            unkown_v_trn.amount, 'vodafone')


