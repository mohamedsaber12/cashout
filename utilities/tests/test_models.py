# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from decimal import Decimal

from django.test import TestCase

from users.tests.factories import SuperAdminUserFactory, VMTDataFactory
from users.models import RootUser

from utilities.models import Budget, FeeSetup, CallWalletsModerator

DISBURSEMENT = 1
DISBURSEMENT_KEYS = ['LOGIN', 'PASSWORD', 'REQUEST_GATEWAY_CODE', 'REQUEST_GATEWAY_TYPE', 'WALLETISSUER', 'SENDERS',
                     'RECIPIENTS', 'PIN', 'SMSSENDER', 'SERVICETYPE', 'SOURCE', 'TYPE']
INSTANT_DISBURSEMENT = 2
INSTANT_DISBURSEMENT_KEYS = ['LOGIN', 'PASSWORD', 'REQUEST_GATEWAY_CODE', 'REQUEST_GATEWAY_TYPE', 'WALLETISSUER',
 'MSISDN', 'MSISDN2', 'AMOUNT', 'PIN', 'IS_REVERSED', 'TYPE']
CHANGE_PROFILE = 3          # List/Bulk of consumers
CHANGE_PROFILE_KEYS = ['LOGIN', 'PASSWORD', 'REQUEST_GATEWAY_CODE', 'REQUEST_GATEWAY_TYPE',
                       'WALLETISSUER', 'USERS', 'NEWPROFILE', 'TYPE']
SET_PIN = 4                 # List/Bulk of agents
SET_PIN_KEYS = ['LOGIN', 'PASSWORD', 'REQUEST_GATEWAY_CODE', 'REQUEST_GATEWAY_TYPE', 'WALLETISSUER',
                'USERS', 'PIN', 'TYPE']
USER_INQUIRY = 5            # List/Bulk of agents/consumers
USER_INQUIRY_KEYS = ['LOGIN', 'PASSWORD', 'REQUEST_GATEWAY_CODE', 'REQUEST_GATEWAY_TYPE',
                     'WALLETISSUER', 'USERS', 'TYPE']
BALANCE_INQUIRY = 6
BALANCE_INQUIRY_KEYS = ['LOGIN', 'PASSWORD', 'REQUEST_GATEWAY_CODE', 'REQUEST_GATEWAY_TYPE',
                        'WALLETISSUER', 'MSISDN', 'PIN', 'TYPE']
DISBURSEMENT_OR_CHANGE_PROFILE_CALLBACK_INQUIRY = 7
DISBURSEMENT_OR_CHANGE_PROFILE_CALLBACK_INQUIRY_KEYS = ['LOGIN', 'PASSWORD', 'REQUEST_GATEWAY_CODE',
                                                        'REQUEST_GATEWAY_TYPE', 'WALLETISSUER', 'BATCH_ID', 'TYPE']
BULK_DISBURSEMENT_PAYLOAD_KEYS = ['LOGIN', 'PASSWORD', 'REQUEST_GATEWAY_CODE', 'REQUEST_GATEWAY_TYPE', 'WALLETISSUER',
                                  'SENDERS', 'RECIPIENTS', 'PIN', 'SERVICETYPE', 'SOURCE', 'TYPE']
INSTANT_DISBURSEMENT_PAYLOAD_KEYS = ['LOGIN', 'PASSWORD', 'REQUEST_GATEWAY_CODE', 'REQUEST_GATEWAY_TYPE',
                                     'WALLETISSUER', 'MSISDN', 'MSISDN2', 'AMOUNT', 'PIN', 'IS_REVERSED', 'TYPE']
CHANGE_PROFILE_PAYLOAD_KEYS = ['LOGIN', 'PASSWORD', 'REQUEST_GATEWAY_CODE', 'REQUEST_GATEWAY_TYPE', 'WALLETISSUER',
                                'USERS', 'NEWPROFILE', 'TYPE']
USER_INQUIRY_PAYLOAD_KEYS = ['LOGIN', 'PASSWORD', 'REQUEST_GATEWAY_CODE', 'REQUEST_GATEWAY_TYPE',
                             'WALLETISSUER', 'USERS', 'TYPE']
SET_PIN_PAYLOAD_KEYS = ['LOGIN', 'PASSWORD', 'REQUEST_GATEWAY_CODE', 'REQUEST_GATEWAY_TYPE', 'WALLETISSUER',
                        'USERS', 'PIN', 'TYPE']
BALANCE_INQUIRY_PAYLOAD_KEYS = ['LOGIN', 'PASSWORD', 'REQUEST_GATEWAY_CODE', 'REQUEST_GATEWAY_TYPE', 'WALLETISSUER',
                                'MSISDN', 'PIN', 'TYPE']


class AbstractBaseVMTDataTests(TestCase):

    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)

    # test return vmt data in case purpose is disbursement
    def test_return_vmt_data_purpose_disbursement(self):
        vmt_data = self.vmt_data_obj.return_vmt_data(DISBURSEMENT)
        self.assertEqual(list(vmt_data.keys()), DISBURSEMENT_KEYS)

    # test return vmt data in case purpose is INSTANT_DISBURSEMENT
    def test_return_vmt_data_purpose_instant_disbursement(self):
        vmt_data = self.vmt_data_obj.return_vmt_data(INSTANT_DISBURSEMENT)
        self.assertEqual(list(vmt_data.keys()), INSTANT_DISBURSEMENT_KEYS)

    # test return vmt data in case purpose is CHANGE_PROFILE
    def test_return_vmt_data_purpose_change_profile(self):
        vmt_data = self.vmt_data_obj.return_vmt_data(CHANGE_PROFILE)
        self.assertEqual(list(vmt_data.keys()), CHANGE_PROFILE_KEYS)

    # test return vmt data in case purpose is SET_PIN
    def test_return_vmt_data_purpose_set_pin(self):
        vmt_data = self.vmt_data_obj.return_vmt_data(SET_PIN)
        self.assertEqual(list(vmt_data.keys()), SET_PIN_KEYS)

    # test return vmt data in case purpose is USER_INQUIRY
    def test_return_vmt_data_purpose_user_inquiry(self):
        vmt_data = self.vmt_data_obj.return_vmt_data(USER_INQUIRY)
        self.assertEqual(list(vmt_data.keys()), USER_INQUIRY_KEYS)

    # test return vmt data in case purpose is BALANCE_INQUIRY
    def test_return_vmt_data_purpose_balance_inquiry(self):
        vmt_data = self.vmt_data_obj.return_vmt_data(BALANCE_INQUIRY)
        self.assertEqual(list(vmt_data.keys()), BALANCE_INQUIRY_KEYS)

    # test return vmt data in case purpose is DISBURSEMENT_OR_CHANGE_PROFILE_CALLBACK_INQUIRY
    def test_return_vmt_data_purpose_disbursement_or_change_profile_callback_inquiry(self):
        vmt_data = self.vmt_data_obj.return_vmt_data(DISBURSEMENT_OR_CHANGE_PROFILE_CALLBACK_INQUIRY)
        self.assertEqual(list(vmt_data.keys()), DISBURSEMENT_OR_CHANGE_PROFILE_CALLBACK_INQUIRY_KEYS)

    # test _refine_payload_pin
    def test_refine_payload_pin(self):
        payload = self.vmt_data_obj.return_vmt_data(DISBURSEMENT)
        payload_without_pin = self.vmt_data_obj._refine_payload_pin(payload)
        self.assertEqual(payload_without_pin.get('PIN', False), False)

    # test accumulate_disbursement_or_change_profile_callback_inquiry_payload
    # with batch id 123
    def test_accumulate_disbursement_or_change_profile_callback_inquiry_payload(self):
        payload = self.vmt_data_obj.accumulate_disbursement_or_change_profile_callback_inquiry_payload('123')
        self.assertEqual(payload.get('BATCH_ID'), '123')

    # test accumulate_disbursement_or_change_profile_callback_inquiry_payload
    # with batch id None
    def test_accumulate_disbursement_or_change_profile_callback_inquiry_payload_without_batch_id(self):
        self.assertRaises(
            ValueError,
            self.vmt_data_obj.accumulate_disbursement_or_change_profile_callback_inquiry_payload,
            None
        )

    # test accumulate_bulk_disbursement_payload
    def test_accumulate_bulk_disbursement_payload_without_agents_attr(self):
        self.assertRaises(
            ValueError,
            self.vmt_data_obj.accumulate_bulk_disbursement_payload,
            None, None, 'test'
        )

    # test accumulate_bulk_disbursement_payload
    def test_accumulate_bulk_disbursement_payload(self):
        payload, payload_without_pin = self.vmt_data_obj.accumulate_bulk_disbursement_payload(
            [{'MSISDN': '01021469732', 'PIN': '123456'}], ['01111451253'], None)
        self.assertEqual(
            list(payload.keys()),
            BULK_DISBURSEMENT_PAYLOAD_KEYS
        )
        self.assertEqual(
            list(payload_without_pin.keys()),
            BULK_DISBURSEMENT_PAYLOAD_KEYS
        )

    # test accumulate_instant_disbursement_payload
    # def test_accumulate_instant_disbursement_payload_with_None_parameters(self):
    #     self.assertRaises(
    #         ValueError,
    #         self.vmt_data_obj.accumulate_instant_disbursement_payload,
    #         None, None, None, None, None
    #     )
    # test accumulate_instant_disbursement_payload
    # def test_accumulate_instant_disbursement_payload(self):
    #     payload, payload_without_pin = self.vmt_data_obj.accumulate_instant_disbursement_payload(
    #         [{'MSISDN': '01021469732', 'PIN': '123456'}],
    #         ['01111451253'], 200, '123456', 'vodafone')
    #     self.assertEqual(
    #         list(payload.keys()),
    #         INSTANT_DISBURSEMENT_PAYLOAD_KEYS
    #     )
    #     self.assertEqual(
    #         list(payload_without_pin.keys()),
    #         INSTANT_DISBURSEMENT_PAYLOAD_KEYS
    #     )

    # test accumulate_change_profile_payload
    def test_accumulate_change_profile_payload_with_None_parameters(self):
        self.assertRaises(
            ValueError,
            self.vmt_data_obj.accumulate_change_profile_payload,
            None, None
        )

    # test accumulate_change_profile_payload
    def test_accumulate_change_profile_payload(self):
        payload = self.vmt_data_obj.accumulate_change_profile_payload(
            [{'MSISDN': '01021469732'}],
           'No fees')
        self.assertEqual(
            list(payload.keys()),
            CHANGE_PROFILE_PAYLOAD_KEYS
        )

    # test accumulate_user_inquiry_payload
    def test_accumulate_user_inquiry_payload_with_None_parameters(self):
        self.assertRaises(
            ValueError,
            self.vmt_data_obj.accumulate_user_inquiry_payload,
            None
        )

    # test accumulate_user_inquiry_payload
    def test_accumulate_user_inquiry_payload(self):
        payload = self.vmt_data_obj.accumulate_user_inquiry_payload(
            [{'MSISDN': '01021469732'}])
        self.assertEqual(
            list(payload.keys()),
            USER_INQUIRY_PAYLOAD_KEYS
        )

    # test accumulate_set_pin_payload
    def test_accumulate_set_pin_payload_with_None_parameters(self):
        self.assertRaises(
            ValueError,
            self.vmt_data_obj.accumulate_set_pin_payload,
            None, None
        )

    # test accumulate_set_pin_payload
    def test_accumulate_set_pin_payload(self):
        payload, payload_without_pin = self.vmt_data_obj.accumulate_set_pin_payload(
                [{'MSISDN': '01021469732', 'PIN': '123456'}],
                '123456')
        self.assertEqual(
            list(payload.keys()),
            SET_PIN_PAYLOAD_KEYS
        )
        self.assertEqual(
            list(payload_without_pin.keys()),
            SET_PIN_PAYLOAD_KEYS
        )

    # test accumulate_balance_inquiry_payload
    def test_accumulate_balance_inquiry_payload_with_None_parameters(self):
        self.assertRaises(
            ValueError,
            self.vmt_data_obj.accumulate_balance_inquiry_payload,
            None, None
        )

    # test accumulate_balance_inquiry_payload
    def test_accumulate_balance_inquiry_payload(self):
        payload, payload_without_pin = self.vmt_data_obj.accumulate_balance_inquiry_payload(
                '01021469732', '123456')
        self.assertEqual(
            list(payload.keys()),
            BALANCE_INQUIRY_PAYLOAD_KEYS
        )
        self.assertEqual(
            list(payload_without_pin.keys()),
            BALANCE_INQUIRY_PAYLOAD_KEYS
        )


class BudgetTests(TestCase):
    def setUp(self):
        self.root = RootUser(id=1, username='test_root_user')
        self.root.root = self.root
        self.root.save()
        self.budget = Budget(disburser=self.root)
        self.budget.save()

    # test budget created successfully
    def test_budget_created_successfully(self):
        self.assertEqual(
            self.budget.__str__(),
            f"{self.budget.disburser.username} Custom Budget"
        )

    # test accumulate_amount_with_fees_and_vat with issuer vodafone
    def test_accumulate_amount_with_fees_and_vat_vodafone(self):
        fees_setup_vodafone = FeeSetup(budget_related=self.budget, issuer='vf',
                                        fee_type='p', percentage_value=2.25)
        fees_setup_vodafone.save()
        self.assertEqual(
            self.budget.accumulate_amount_with_fees_and_vat(200, 'V'),
            Decimal('205.13')
        )

    # test accumulate_amount_with_fees_and_vat with issuer etisalat
    def test_accumulate_amount_with_fees_and_vat_etisalat(self):
        fees_setup_etisalat = FeeSetup(
            budget_related=self.budget, issuer='es', fee_type='p',
            percentage_value=2.25, min_value=10)
        fees_setup_etisalat.save()
        self.assertEqual(
            self.budget.accumulate_amount_with_fees_and_vat(200, 'E'),
            Decimal('211.4')
        )

    # test accumulate_amount_with_fees_and_vat with issuer orange
    def test_accumulate_amount_with_fees_and_vat_orange(self):
        fees_setup_orange = FeeSetup(
            budget_related=self.budget, issuer='og', fee_type='p',
            percentage_value=2.25, max_value=3)
        fees_setup_orange.save()
        self.assertEqual(
            self.budget.accumulate_amount_with_fees_and_vat(200, 'O'),
            Decimal('203.42')
        )

    # test accumulate_amount_with_fees_and_vat with issuer aman
    def test_accumulate_amount_with_fees_and_vat_aman(self):
        fees_setup_aman = FeeSetup(budget_related=self.budget, issuer='am',
                                        fee_type='p', percentage_value=2.25)
        fees_setup_aman.save()
        self.assertEqual(
            self.budget.accumulate_amount_with_fees_and_vat(200, 'A'),
            Decimal('205.13')
        )

    # test accumulate_amount_with_fees_and_vat with issuer bank wallet
    def test_accumulate_amount_with_fees_and_vat_bank_wallet(self):
        fees_setup_bank_wallet = FeeSetup(budget_related=self.budget, issuer='bw',
                                       fee_type='p', percentage_value=2.25)
        fees_setup_bank_wallet.save()
        self.assertEqual(
            self.budget.accumulate_amount_with_fees_and_vat(200, 'B'),
            Decimal('205.13')
        )
    # test accumulate_amount_with_fees_and_vat with fake fees
    def test_accumulate_amount_with_fees_and_vat_fake_fees(self):
        self.assertRaises(
            ValueError,
            self.budget.accumulate_amount_with_fees_and_vat,
            200, 'C'
        )

    # test calculate_fees_and_vat_for_amount with issuer vodafone
    def test_calculate_fees_and_vat_for_amount_vodafone(self):
        fees_setup_vodafone = FeeSetup(budget_related=self.budget, issuer='vf',
                                       fee_type='p', percentage_value=2.25)
        fees_setup_vodafone.save()
        fees, vat = self.budget.calculate_fees_and_vat_for_amount(200, 'V')
        self.assertEqual(
            fees,
            Decimal('4.5')
        )
        self.assertEqual(
            vat,
            Decimal('0.63')
        )

    # test calculate_fees_and_vat_for_amount with issuer etisalat
    def test_calculate_fees_and_vat_for_amount_etisalat(self):
        fees_setup_etisalat = FeeSetup(
                budget_related=self.budget, issuer='es', fee_type='p',
                percentage_value=2.25, min_value=10)
        fees_setup_etisalat.save()
        fees, vat = self.budget.calculate_fees_and_vat_for_amount(200, 'E')
        self.assertEqual(
                fees,
                Decimal('10')
        )
        self.assertEqual(
                vat,
                Decimal('1.4000')
        )

    # test calculate_fees_and_vat_for_amount with issuer orange
    def test_calculate_fees_and_vat_for_amount_orange(self):
        fees_setup_orange = FeeSetup(
                budget_related=self.budget, issuer='og', fee_type='p',
                percentage_value=2.25, max_value=3)
        fees_setup_orange.save()
        fees, vat = self.budget.calculate_fees_and_vat_for_amount(200, 'O')
        self.assertEqual(
                fees,
                Decimal('3')
        )
        self.assertEqual(
                vat,
                Decimal('0.4200')
        )

    # test calculate_fees_and_vat_for_amount with issuer aman
    def test_calculate_fees_and_vat_for_amount_aman(self):
        fees_setup_aman = FeeSetup(budget_related=self.budget, issuer='am',
                                   fee_type='p', percentage_value=2.25)
        fees_setup_aman.save()
        fees, vat = self.budget.calculate_fees_and_vat_for_amount(200, 'A')
        self.assertEqual(
                fees,
                Decimal('4.5')
        )
        self.assertEqual(
                vat,
                Decimal('0.63')
        )

    # test calculate_fees_and_vat_for_amount with issuer bank wallet
    def test_calculate_fees_and_vat_for_amount_bank_wallet(self):
        fees_setup_bank_wallet = FeeSetup(budget_related=self.budget, issuer='bw',
                                          fee_type='p', percentage_value=2.25)
        fees_setup_bank_wallet.save()
        fees, vat = self.budget.calculate_fees_and_vat_for_amount(200, 'B')
        self.assertEqual(
                fees,
                Decimal('4.5000')
        )
        self.assertEqual(
                vat,
                Decimal('0.6300')
        )

    # test calculate_fees_and_vat_for_amount with issuer bank card
    def test_calculate_fees_and_vat_for_amount_bank_card(self):
        fees_setup_bank_wallet = FeeSetup(budget_related=self.budget, issuer='bc',
                                          fee_type='f', fixed_value=20)
        fees_setup_bank_wallet.save()
        fees, vat = self.budget.calculate_fees_and_vat_for_amount(200, 'C')
        self.assertEqual(
            fees,
            Decimal('20')
        )
        self.assertEqual(
            vat,
            Decimal('2.8000')
        )

    # test calculate_fees_and_vat_for_amount with issuer default
    def test_calculate_fees_and_vat_for_amount_default(self):
        fees_setup_bank_wallet = FeeSetup(budget_related=self.budget, issuer='bw',
                                          fee_type='p', percentage_value=2.25)
        fees_setup_bank_wallet.save()
        fees, vat = self.budget.calculate_fees_and_vat_for_amount(200, 'default')
        self.assertEqual(
            fees,
            Decimal('0')
        )
        self.assertEqual(
            vat,
            Decimal('0')
        )

    # test calculate_fees_and_vat_for_amount with fake fees
    def test_calculate_fees_and_vat_for_amount_fake_fees(self):
        self.assertRaises(
            ValueError,
            self.budget.calculate_fees_and_vat_for_amount,
            200, 'C'
        )

    # test within_threshold
    def test_within_threshold_with_None_value(self):
        fees_setup_bank_wallet = FeeSetup(budget_related=self.budget, issuer='bw',
                                          fee_type='p', percentage_value=2.25)
        fees_setup_bank_wallet.save()
        self.assertRaises(
            ValueError,
            self.budget.within_threshold,
            200, None
        )

    # test within_threshold
    def test_within_threshold(self):
        fees_setup_bank_wallet = FeeSetup(budget_related=self.budget, issuer='bw',
                                        fee_type='p', percentage_value=2.25)
        fees_setup_bank_wallet.save()
        self.budget.current_balance = Decimal('10000')
        self.assertEqual(
            self.budget.within_threshold(200, 'bank_wallet'),
            True
        )

    #  test url for current budget is correct
    def test_get_absolute_url(self):
        self.assertEqual(
            self.budget.get_absolute_url(),
            f"/budget/edit/{self.budget.disburser.username}/"
        )

    # test update_disbursed_amount_and_current_balance
    def test_update_disbursed_amount_and_current_balance_None_values(self):
        self.assertRaises(
            ValueError,
            self.budget.update_disbursed_amount_and_current_balance,
            200, None
        )

    # test update_disbursed_amount_and_current_balance
    def test_update_disbursed_amount_and_current_balance(self):
        fees_setup_bank_wallet = FeeSetup(budget_related=self.budget, issuer='bw',
                                          fee_type='p', percentage_value=2.25)
        fees_setup_bank_wallet.save()
        self.assertEqual(
            self.budget.update_disbursed_amount_and_current_balance(200, 'bank_wallet'),
            True
        )

    # test return_disbursed_amount_for_cancelled_trx
    def test_return_disbursed_amount_for_cancelled_trx_None_values(self):
        self.assertRaises(
            ValueError,
            self.budget.return_disbursed_amount_for_cancelled_trx,
            None
        )

    # test return_disbursed_amount_for_cancelled_trx
    def test_return_disbursed_amount_for_cancelled_trx(self):
        self.assertEqual(
            self.budget.return_disbursed_amount_for_cancelled_trx(200),
            True
        )

class FeeSetupTests(TestCase):

    def setUp(self):
        self.root = RootUser(id=1, username='test_root_user')
        self.root.root = self.root
        self.root.save()
        self.budget = Budget(disburser=self.root)
        self.budget.save()
        self.fees_setup_bank_wallet = FeeSetup(
            budget_related=self.budget, issuer='bw',
            fee_type='p', percentage_value=2.25
        )
        self.fees_setup_bank_wallet.save()

    # test feesSetup created successfully
    def test_feesSetup_created_successfully(self):
        self.assertEqual(
            self.fees_setup_bank_wallet.__str__(),
            f"{self.fees_setup_bank_wallet.fee_type_choice_verbose} setup for"
            f" {self.fees_setup_bank_wallet.issuer_choice_verbose}"
        )

    # test issuer_choice_verbose
    def test_issuer_choice_verbose(self):
        self.assertEqual(
            self.fees_setup_bank_wallet.issuer_choice_verbose,
            'Bank Wallet'
        )

    # test fee_type_choice_verbose
    def test_fee_type_choice_verbose(self):
        self.assertEqual(
            self.fees_setup_bank_wallet.fee_type_choice_verbose,
            'Percentage Fee'
        )


class CallWalletsModeratorTests(TestCase):

    def setUp(self):
        self.root = RootUser(id=1, username='test_root_user')
        self.root.root = self.root
        self.root.save()
        self.call_wallets_moderators = CallWalletsModerator(user_created=self.root)
        self.call_wallets_moderators.save()

    # test CallWalletsModerator object created successfully with root
    def test_call_wallets_moderator_created_successfully(self):
        self.assertEqual(
            self.call_wallets_moderators.__str__(),
            f"{self.root.username} moderator"
        )