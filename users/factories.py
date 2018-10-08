import factory

from users.models import User
from faker import Factory as fakeFactory

fake = fakeFactory.create()


class UserFactory(factory.django.DjangoModelFactory):
    username = fake.user_name()
    email = fake.email()
    mobile_no = '0'
    is_parent = True
    password = fake.password()
    is_staff = True


class DisbursementUserFactory(UserFactory):
    class Meta:
        model = User
        abstract = False