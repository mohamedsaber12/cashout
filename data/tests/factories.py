import factory
import factory.django

from data.models import FileCategory
from users.tests.factories import AdminUserFactory
from users.models import User
from faker import Factory


fake = Factory.create()


class DisbursementFileCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FileCategory

    user_created = factory.SubFactory(AdminUserFactory)
    name = 'test'
    unique_field = 'MSISDN'
    amount_field = 'Amount'
    category_type = 2