# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory
from faker import Factory as fakeFactory

from .models import (
    Agent, VMTData, DisbursementDocData, DisbursementData, BankTransaction
)
from .utils import VALID_BANK_CODES_LIST


fake = fakeFactory.create()


class VMTDataFactory(factory.django.DjangoModelFactory):
    """
    Factory model for creating corresponding VMT data object for the superadmin users
    """

    login_username = "DISBURSEMENT"
    login_password = "DISBURSEMENT"
    request_gateway_code = "DISBURSEMENT"
    request_gateway_type = "DISBURSEMENT"
    wallet_issuer = "VODAFONE"
    vmt_environment = "STAGING"
    vmt = factory.Sequence(lambda obj: "superadmin")

    class Meta:
        model = VMTData


class AgentFactory(factory.django.DjangoModelFactory):
    """
    Factory model for creating agents
    """

    msisdn = factory.Sequence(lambda obj: fake.numerify(text="010########"))
    pin = factory.Sequence(lambda obj: fake.boolean())
    super = factory.Sequence(lambda obj: fake.boolean())
    type = factory.Sequence(lambda obj: fake.random_element(["V", "E"]))
    wallet_provider = factory.Sequence(lambda obj: "superadmin")

    class Meta:
        model = Agent


class VariousAgentFactory:
    """
    Factory model consumes the main AgentFactory model to create super-agents and agents
    for specific (wallet issuer / agent provider) user
    """

    @staticmethod
    def super_agent(agent_provider):
        """Create super-agent for specific user"""
        return AgentFactory(msisdn="01006333714", pin=True, super=True, type="V", wallet_provider=agent_provider)

    @staticmethod
    def vodafone_agent(agent_provider):
        """Create vodafone-agent for specific user"""
        return AgentFactory(msisdn="01006332833", pin=True, super=False, type="V", wallet_provider=agent_provider)

    @staticmethod
    def etisalat_agent(agent_provider):
        """Create etisalat-agent for specific user"""
        return AgentFactory(msisdn="01100926774", pin=True, super=False, type="E", wallet_provider=agent_provider)

    @staticmethod
    def mandatory_agents(agent_provider):
        """Create the mandatory agents to complete the onboarding setups of specific user (superadmin/admin)"""
        VariousAgentFactory.super_agent(agent_provider=agent_provider)
        VariousAgentFactory.vodafone_agent(agent_provider=agent_provider)
        VariousAgentFactory.etisalat_agent(agent_provider=agent_provider)


class DisbursementDocDataFactory(factory.django.DjangoModelFactory):
    """
    factory model for Disbursement Doc Data model
    """
    # doc = models.OneToOneField('data.Doc', null=True, related_name='disbursement_txn', on_delete=models.CASCADE)
    txn_id = "dmf9023mlsad"
    # doc_status = factory.Iterator(DisbursementDocData.STATUS_CHOICES)
    has_callback = True
    txn_status = True

    class Meta:
        model = DisbursementDocData


class DisbursementDataFactory(factory.django.DjangoModelFactory):
    """
    factory model for Disbursement Data model
    """

    # doc = models.ForeignKey('data.Doc', null=True, related_name='disbursement_data', on_delete=models.CASCADE)
    is_disbursed = factory.LazyFunction(fake.boolean)
    amount = factory.LazyFunction(fake.numerify)
    msisdn = factory.Sequence(lambda obj: fake.numerify(text="010########"))
    issuer = factory.Iterator(['default', 'vodafone', 'etisalat', 'aman', 'orange'])
    reason = factory.LazyAttribute(
            lambda obj: 'SUCCESS' if obj.is_disbursed else fake.text()
    )
    reference_id = factory.LazyFunction(fake.numerify)
    # aman_obj = GenericRelation(
    #         "instant_cashin.AmanTransaction",
    #         object_id_field="transaction_id",
    #         content_type_field="transaction_type",
    #         related_query_name="aman_manual"
    # )


    class Meta:
        model = DisbursementData


class BankTransactionFactory(factory.django.DjangoModelFactory):
    """
    factory model for bank transaction model
    """
    # user_created = models.ForeignKey(
    #         settings.AUTH_USER_MODEL,
    #         on_delete=models.CASCADE,
    #         related_name=_('bank_transactions'),
    #         verbose_name=_('Disburser')
    # )
    # document = models.ForeignKey(
    #         'data.Doc',
    #         on_delete=models.CASCADE,
    #         related_name=_('bank_cards_transactions'),
    #         verbose_name=_('Bank Cards Document'),
    #         null=True
    # )
    # parent_transaction = models.ForeignKey(
    #         'self',
    #         on_delete=models.CASCADE,
    #         related_name=_('children_transactions'),
    #         verbose_name=_('Parent Transaction'),
    #         null=True
    # )
    transaction_id = factory.LazyFunction(fake.uuid4)
    message_id = factory.LazyFunction(fake.uuid4)

    # transaction_status_code = models.CharField(
    #         _('Transaction Status Code'),
    #         max_length=6,
    #         blank=True,
    #         null=True
    # )
    transaction_status_description = factory.LazyFunction(fake.text)
    debtor_account = factory.Sequence(lambda obj: fake.numerify(text="1###########"))
    amount = factory.LazyFunction(fake.numerify)

    creditor_name = factory.LazyFunction(fake.first_name)
    creditor_account_number = factory.Sequence(lambda obj: fake.numerify(text="1###############"))
    creditor_bank = factory.Iterator(VALID_BANK_CODES_LIST)
    creditor_email = factory.LazyFunction(fake.email)
    creditor_mobile_number = factory.Sequence(lambda obj: fake.numerify(text="010########"))

    corporate_code = 'PAYMOBCO'

    is_single_step = factory.LazyFunction(fake.boolean)

    class Meta:
        model = BankTransaction