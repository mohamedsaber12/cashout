import factory
import faker
from django.contrib.auth.hashers import make_password

from users.factories import DisbursementUserFactory
from . import models

fake = faker.Factory.create()


class VMTDataFactory(factory.Factory):
    class Meta:
        model = models.VMTData

    login_username = 'DISBURSEMENT'
    login_password = 'DISBURSEMENT'
    request_gateway_code = 'DISBURSEMENT'
    request_gateway_type = 'DISBURSEMENT'
    wallet_issuer = 'DISBURSEMENT'
    vmt = factory.SubFactory(DisbursementUserFactory)
    vmt_environment = 'STAGING'


class AgentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Agent

    wallet_provider = factory.SubFactory(DisbursementUserFactory)
    msisdn = fake.numerify(text='01#########')
    pin = make_password('123456')