# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from users.tests.factories import SuperAdminUserFactory, VMTDataFactory

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
    def test_accumulate_instant_disbursement_payload_with_None_parameters(self):
        self.assertRaises(
            ValueError,
            self.vmt_data_obj.accumulate_instant_disbursement_payload,
            None, None, None, None, None
        )
    # test accumulate_instant_disbursement_payload
    def test_accumulate_instant_disbursement_payload(self):
        payload, payload_without_pin = self.vmt_data_obj.accumulate_instant_disbursement_payload(
            [{'MSISDN': '01021469732', 'PIN': '123456'}],
            ['01111451253'], 200, '123456', 'vodafone')
        self.assertEqual(
            list(payload.keys()),
            INSTANT_DISBURSEMENT_PAYLOAD_KEYS
        )
        self.assertEqual(
            list(payload_without_pin.keys()),
            INSTANT_DISBURSEMENT_PAYLOAD_KEYS
        )

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