# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import factory
from faker import Factory as fakeFactory

from .models import Agent, VMTData


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
