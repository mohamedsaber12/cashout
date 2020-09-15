# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from celery import Task

from data.models import Doc
from payouts.settings.celery import app
from users.models import User
from utilities.functions import custom_budget_logger, get_value_from_env

from .models import DisbursementData, DisbursementDocData


DATA_LOGGER = logging.getLogger("disburse")


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

        return list(etisalat_recipients), list(orange_recipients)

    def handle_etisalat_disbursement_callback(self, txn_id, callback):
        """Handle etisalat issuer based recipients callback at the etisalat disbursement loop"""
        try:
            callback_json = callback.json()
            disbursement_data_record = DisbursementData.objects.get(id=txn_id)
            disbursement_data_record.is_disbursed = True if callback_json['TXNSTATUS'] == '200' else False
            disbursement_data_record.reason = callback_json['TXNSTATUS']
            doc_obj = disbursement_data_record.doc

            if callback_json['TXNSTATUS'] == '200':
                doc_obj.owner.root.budget. \
                    update_disbursed_amount_and_current_balance(disbursement_data_record.amount, "etisalat")
                custom_budget_logger(
                        doc_obj.owner.root.username,
                        f"Total disbursed amount: {disbursement_data_record.amount} LE",
                        doc_obj.owner.user.username, f" -- doc id: {doc_obj.doc_id}"
                )

            disbursement_data_record.save()
            return True
        except (DisbursementData.DoesNotExist, Exception):
            return False

    def disburse_for_etisalat(self, checker, superadmin, ets_recipients):
        """Disburse etisalat specific recipients"""
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
            self.handle_etisalat_disbursement_callback(recipient['txn_id'], ets_callback)

    def run(self, doc_id, checker_username, *args, **kwargs):
        """
        :param doc_id: id of the document being disbursed
        :param checker_username: username of the checker who is taking the disbursement action
        :return
        """
        try:
            doc_obj = Doc.objects.get(id=doc_id)
            checker = User.objects.get(username=checker_username)
            superadmin = checker.root.client.creator
            ets_recipients, orange_recipients = self.separate_recipients(doc_obj.id)

            if ets_recipients:
                self.disburse_for_etisalat(checker, superadmin, ets_recipients)
            elif orange_recipients:
                pass

            DisbursementDocData.objects.filter(doc=doc_obj).update(has_callback=True)

        except (Doc.DoesNotExist, User.DoesNotExist, Exception) as err:
            DATA_LOGGER.debug(f"[DISBURSE BULK ERROR - ONE STEP RECORDS TASK]\nUser: {checker_username}\n{err}")
            return None


BulkDisbursementThroughOneStepCashin = app.register_task(BulkDisbursementThroughOneStepCashin())
