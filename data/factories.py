import factory
import factory.django

from data.models import FileCategory
from users.factories import DisbursementUserFactory
from users.models import User
from faker import Factory


fake = Factory.create()


class DisbursementFileCategory(factory.django.DjangoModelFactory):
    class Meta:
        model = FileCategory

    identifier1 = 'MSISDN'
    identifier2 = 'Amount'
    identifier3 = 'Name'
    user_created = factory.SubFactory(DisbursementUserFactory)
    name = 'test'
    has_header = True
    unique_field = 'MSISDN'
    amount_field = 'Amount'
    category_type = 2