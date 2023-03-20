# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import Permission
from django.test import Client, RequestFactory, TestCase

from disbursement.forms import (AgentForm, BalanceInquiryPinForm,
                                ExistingAgentForm, PinForm,
                                SingleStepTransactionForm, VMTDataForm)
from disbursement.models import Agent
from users.models import Brand, CheckerUser
from users.models import Client as ClientModel
from users.models import (EntitySetup, InstantAPICheckerUser,
                          InstantAPIViewerUser, Levels, MakerUser, RootUser,
                          Setup, SuperAdminUser, SupportSetup, SupportUser,
                          UpmakerUser, User)
from users.tests.factories import (AdminUserFactory, SuperAdminUserFactory,
                                   VMTDataFactory)
from utilities.models import (AbstractBaseDocType, Budget,
                              CallWalletsModerator, FeeSetup)

# -*- coding: utf-8 -*-




REQUIRED_FIELD_ERROR = 'This field is required.'
MOBILE_NUMBER_ERROR = 'Mobile number is not valid'
MOBILE_INVALID_CHOICE_ERROR = (
    'Select a valid choice. 01021y79732 is not one of the available choices.'
)
PIN_IS_NUMERIC_ERROR = 'Pin must be numeric'
PIN_IS_INVALID = 'Invalid pin'
AMOUNT_ERROR = 'Enter a whole number.'
AMOUNT_EXCEEDED_MAXIMUM_AMOUNT_CAN_BE_DISBURSED = (
    'Entered amount exceeds your maximum amount that can be disbursed'
)
AMOUNT_EXCEEDS_CURRENT_BALANCE = 'Entered amount exceeds your current balance'
INVALID_ISSUER_ERROR = 'issuer must be one of these \
bank_card / Bank Card / vodafone / etisalat / orange / bank_wallet / aman'
ACCOUNT_NUMBER_ERROR = 'Invalid Account number'
CREDITOR_NAME_ERROR = 'Symbols like !%*+&,<=> not allowed in full name'
FIRST_NAME_ERROR = 'Symbols like !%*+&,<=> not allowed in first name'
LAST_NAME_ERROR = 'Symbols like !%*+&,<=> not allowed in last name'
CREDITOR_NAME_INVALID = 'Invalid name'
VMT_ENVIRONMENT = 'PRODUCTION'
INVALID_ISSUER_CHOICE = (
    'Select a valid choice. xyz is not one of the available choices.'
)
INVALID_MSISDN_ERROR = 'The string supplied did not seem to be a phone number.'


class VMTDataFormTests(TestCase):
    def setUp(self):
        self.root = RootUser(id=1, username='test_root_user')
        self.root.root = self.root
        self.root.save()

    # test login_username exist in form data
    def test_login_username_not_exist(self):
        form_data = {}
        vmtForm = VMTDataForm(data=form_data, root=self.root)
        self.assertEqual(vmtForm.is_valid(), False)
        self.assertEqual(vmtForm.errors['login_username'], [REQUIRED_FIELD_ERROR])

    # test login_password exist in form data
    def test_login_password_not_exist(self):
        form_data = {}
        vmtForm = VMTDataForm(data=form_data, root=self.root)
        self.assertEqual(vmtForm.is_valid(), False)
        self.assertEqual(vmtForm.errors['login_password'], [REQUIRED_FIELD_ERROR])

    # test request_gateway_code exist in form data
    def test_request_gateway_code_not_exist(self):
        form_data = {}
        vmtForm = VMTDataForm(data=form_data, root=self.root)
        self.assertEqual(vmtForm.is_valid(), False)
        self.assertEqual(vmtForm.errors['request_gateway_code'], [REQUIRED_FIELD_ERROR])

    # test request_gateway_type exist in form data
    def test_request_gateway_type_not_exist(self):
        form_data = {}
        vmtForm = VMTDataForm(data=form_data, root=self.root)
        self.assertEqual(vmtForm.is_valid(), False)
        self.assertEqual(vmtForm.errors['request_gateway_type'], [REQUIRED_FIELD_ERROR])

    # test wallet_issuer exist in form data
    def test_wallet_issuer_not_exist(self):
        form_data = {}
        vmtForm = VMTDataForm(data=form_data, root=self.root)
        self.assertEqual(vmtForm.is_valid(), False)
        self.assertEqual(vmtForm.errors['wallet_issuer'], [REQUIRED_FIELD_ERROR])

    # test form save method
    def test_form_saves_values_to_instance_vmt_on_save(self):
        form_data = {
            'login_username': 'test',
            'login_password': 'test',
            'request_gateway_code': 'test',
            'request_gateway_type': 'test',
            'wallet_issuer': 'test',
        }
        vmtForm = VMTDataForm(root=self.root, data=form_data)
        self.assertEqual(vmtForm.is_valid(), True)
        if vmtForm.is_valid():
            vmt = vmtForm.save()
            self.assertEquals(vmt.vmt_environment, VMT_ENVIRONMENT)


class AddAgentFormTests(TestCase):
    def setUp(self):
        self.root = RootUser(id=1, username='test_root_user')
        self.root.root = self.root

    # test msisdn exist in form data
    def test_msisdn_not_exist(self):
        form_data = {}
        form = AgentForm(data=form_data, root=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['msisdn'], [REQUIRED_FIELD_ERROR])

    # test msisdn exist and match agent mobile number
    def test_msisdn_is_mobile_number(self):
        form_data = {'msisdn': '01021469732'}
        form = AgentForm(data=form_data, root=self.root)
        self.assertEqual(form.is_valid(), True)

    # test msisdn exist and not match agent mobile number
    def test_msisdn_not_valid_mobile_number(self):
        form_data = {'msisdn': '01021y79732'}
        form = AgentForm(data=form_data, root=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['msisdn'], [MOBILE_NUMBER_ERROR])


class AddExistingAgentFormTests(TestCase):
    def setUp(self):
        self.root = RootUser(id=1, username='test_root_user')
        self.root.root = self.root
        self.agent_choices = [('01021469732', '01021469732')]

    # test msisdn exist in form data
    def test_msisdn_not_exist(self):
        form_data = {}
        form = ExistingAgentForm(
            data=form_data, root=self.root, agents_choices=self.agent_choices
        )
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['msisdn'], [REQUIRED_FIELD_ERROR])

    # test msisdn exist and match agent mobile number
    def test_msisdn_is_mobile_number(self):
        form_data = {'msisdn': '01021469732'}
        form = ExistingAgentForm(
            data=form_data, root=self.root, agents_choices=self.agent_choices
        )
        self.assertEqual(form.is_valid(), True)

    # test msisdn not exist in choices
    def test_msisdn_not_exist_in_agents(self):
        form_data = {'msisdn': '01021579732'}
        form = ExistingAgentForm(
            data=form_data, root=self.root, agents_choices=self.agent_choices
        )
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(
            form.errors['msisdn'],
            ['Select a valid choice. 01021579732 is not one of the available choices.'],
        )

    # test msisdn exist and not match agent mobile number
    def test_msisdn_not_valid_mobile_number(self):
        self.agent_choices = [('0102y469732', '0102y469732')]
        form_data = {'msisdn': '0102y469732'}
        form = ExistingAgentForm(
            data=form_data, root=self.root, agents_choices=self.agent_choices
        )
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['msisdn'], [MOBILE_NUMBER_ERROR])


class PinFormTests(TestCase):
    def setUp(self):
        self.root = RootUser(id=1, username='test_root_user')
        self.root.root = self.root
        self.root.save()

    # test __init__ method
    def test_init_form(self):
        # make self.root has default vodafone onboarding permission
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='vodafone_default_onboarding'
            )
        )
        form_data = {'pin': '323487'}
        form = PinForm(data=form_data, root=self.root)
        self.assertEqual(form.is_valid(), True)

    #  test get form is None when root has default vodafone onboarding permission
    def test_get_form_is_None(self):
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='vodafone_default_onboarding'
            )
        )
        agent = Agent(
            msisdn='01021469732', type='V', wallet_provider=self.root, pin=True
        )
        agent.save()
        form_data = {}
        form = PinForm(data=form_data, root=self.root).get_form()
        self.assertEqual(form, None)

    #  test get form is Not None
    def test_get_form_is_Not_None(self):
        form_data = {}
        form = PinForm(data=form_data, root=self.root).get_form()
        self.assertNotEqual(form, None)

    # test pin exist in form data
    def test_pin_not_exist(self):
        form_data = {}
        form = PinForm(data=form_data, root=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['pin'], [REQUIRED_FIELD_ERROR])

    # test pin exist in form data
    def test_pin_exist_and_numeric(self):
        form_data = {'pin': '323487'}
        form = PinForm(data=form_data, root=self.root)
        self.assertEqual(form.is_valid(), True)

    # test pin exist in form data
    def test_pin_exist_and_not_numeric(self):
        form_data = {'pin': '32t487'}
        form = PinForm(data=form_data, root=self.root)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['pin'], [PIN_IS_NUMERIC_ERROR])


class BalanceInquiryPinFormTests(TestCase):

    # test pin exist in form data
    def test_pin_not_exist(self):
        form_data = {}
        form = BalanceInquiryPinForm(data=form_data)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['pin'], [REQUIRED_FIELD_ERROR])

    # test pin exist in form data
    def test_pin_exist_and_numeric(self):
        form_data = {'pin': '323487'}
        form = BalanceInquiryPinForm(data=form_data)
        self.assertEqual(form.is_valid(), True)

    # test pin exist in form data
    def test_pin_exist_and_not_numeric(self):
        form_data = {'pin': '32t487'}
        form = BalanceInquiryPinForm(data=form_data)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['pin'], [PIN_IS_NUMERIC_ERROR])


class SingleStepTransactionFormTests(TestCase):
    def setUp(self):
        self.super_admin = SuperAdminUserFactory()
        self.vmt_data_obj = VMTDataFactory(vmt=self.super_admin)
        self.root = AdminUserFactory(user_type=3)
        self.root.root = self.root
        self.brand = Brand(mail_subject='')
        self.brand.save()
        self.root.brand = self.brand
        self.root.save()
        self.agent = Agent(msisdn='01021469732', wallet_provider=self.root, super=True)
        self.agent.save()
        self.root.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='users', codename='has_disbursement'
            )
        )
        self.client_user = ClientModel(client=self.root, creator=self.super_admin)
        self.client_user.save()
        self.setup = Setup.objects.create(
            user=self.root,
            levels_setup=True,
            maker_setup=True,
            checker_setup=True,
            category_setup=False,
            pin_setup=True,
        )
        self.entity_setup = EntitySetup.objects.create(
            user=self.super_admin,
            entity=self.root,
            agents_setup=False,
            fees_setup=False,
        )

        self.request = RequestFactory()
        self.client = Client()

        self.checker_user = CheckerUser.objects.create(
            id=1695,
            username='test1_checker_user',
            email='ch@checkersd1.com',
            root=self.root,
            user_type=2,
        )
        self.root.set_pin("123456")
        self.root.save()

    # test pin exist in form data
    def test_pin_not_exist(self):
        form_data = {}
        form = SingleStepTransactionForm(data=form_data, current_user=self.checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['pin'], ['This field is required.'])

    # test pin exist in form data
    def test_pin_exist_and_invalid(self):
        form_data = {'pin': '323487'}
        form = SingleStepTransactionForm(data=form_data, current_user=self.checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['pin'], ['Invalid pin'])

    # test pin exist in form data
    def test_pin_exist_and_not_numeric(self):
        form_data = {'pin': '32t487'}
        form = SingleStepTransactionForm(data=form_data, current_user=self.checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['pin'], [PIN_IS_NUMERIC_ERROR])

    # test amount exist in form data
    def test_amount_not_exist(self):
        form_data = {}
        form = SingleStepTransactionForm(data=form_data, current_user=self.checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['amount'], [REQUIRED_FIELD_ERROR])

    # test amount invalid in form data
    def test_amount_exist_and_invalid(self):
        form_data = {'amount': 't'}
        form = SingleStepTransactionForm(data=form_data, current_user=self.checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['amount'], [AMOUNT_ERROR])

    # test amount exceeds maximum amount that can be disbursed
    def test_amount_exceeds_maximum_amount_that_can_be_disbursed(self):
        level = Levels(
            max_amount_can_be_disbursed=100, level_of_authority=1, created=self.root
        )
        level.save()
        self.checker_user.level = level
        self.checker_user.save()
        budget = Budget(disburser=self.root)
        # print("===========888")
        budget.current_balance = 1000
        print(budget.__dict__)
        # print("=========888")
        budget.save()
        fees_setup = FeeSetup(
            budget_related=budget, issuer='bc', fee_type='f', fixed_value=5
        )
        fees_setup.save()
        form_data = {'amount': 400, 'issuer': 'bank_card'}
        form = SingleStepTransactionForm(data=form_data, current_user=self.checker_user)
        self.assertEqual(form.is_valid(), False)
        print("===============11")
        print(form.errors)
        self.assertEqual(
            form.errors['amount'], [AMOUNT_EXCEEDED_MAXIMUM_AMOUNT_CAN_BE_DISBURSED]
        )

    # test amount exceeds current balance
    def test_amount_exceeds_current_balance(self):
        self.checker_user.level = Levels(
            max_amount_can_be_disbursed=600, level_of_authority=1, created=self.root
        )
        budget = Budget(disburser=self.root)
        budget.save()
        fees_setup = FeeSetup(
            budget_related=budget, issuer='bc', fee_type='f', fixed_value=5
        )
        fees_setup.save()
        form_data = {'amount': 500, 'issuer': 'bank_card'}
        form = SingleStepTransactionForm(data=form_data, current_user=self.checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['amount'], [AMOUNT_EXCEEDS_CURRENT_BALANCE])

    # test issuer exist in form data
    def test_issuer_not_exist(self):
        form_data = {}
        form = SingleStepTransactionForm(data=form_data, current_user=self.checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['issuer'], [REQUIRED_FIELD_ERROR])

    # test issuer invalid in form data
    def test_issuer_invalid(self):
        form_data = {'issuer': 'xyz'}
        form = SingleStepTransactionForm(data=form_data, current_user=self.checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['issuer'], [INVALID_ISSUER_CHOICE])

    # test msisdn invalid in form ata
    def test_msisdn_invalid(self):
        form_data = {'issuer': 'vodafone'}
        form = SingleStepTransactionForm(data=form_data, current_user=self.checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['msisdn'], [INVALID_MSISDN_ERROR])

    # test creditor_account_number in valid
    def test_creditor_account_number_is_invalid(self):
        form_data = {'creditor_account_number': '12534', 'issuer': 'bank_card'}
        form = SingleStepTransactionForm(data=form_data, current_user=self.checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['creditor_account_number'], [ACCOUNT_NUMBER_ERROR])

    # test account name is invalid
    def test_creditor_name_is_invalid(self):
        form_data = {'creditor_name': '', 'issuer': 'bank_card'}
        form = SingleStepTransactionForm(data=form_data, current_user=self.checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['creditor_name'], [CREDITOR_NAME_INVALID])

    # test account name has symbol
    def test_creditor_name_has_symbol(self):
        form_data = {'creditor_name': 'ddf%!+uhy', 'issuer': 'bank_card'}
        form = SingleStepTransactionForm(data=form_data, current_user=self.checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['creditor_name'], [CREDITOR_NAME_ERROR])

    # test full name has symbol
    def test_full_name_has_symbol(self):
        form_data = {'full_name': 'ddf%!+uhy', 'issuer': 'orange'}
        form = SingleStepTransactionForm(data=form_data, current_user=self.checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['full_name'], [CREDITOR_NAME_ERROR])

    # test first name has symbol
    def test_first_name_has_symbol(self):
        form_data = {'first_name': 'ddf%!+uhy', 'issuer': 'aman'}
        form = SingleStepTransactionForm(data=form_data, current_user=self.checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['first_name'], [FIRST_NAME_ERROR])

    # test last name has symbol
    def test_last_name_has_symbol(self):
        form_data = {'last_name': 'ddf%!+uhy', 'issuer': 'aman'}
        form = SingleStepTransactionForm(data=form_data, current_user=self.checker_user)
        self.assertEqual(form.is_valid(), False)
        self.assertEqual(form.errors['last_name'], [LAST_NAME_ERROR])
