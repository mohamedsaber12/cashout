from faker import Factory as fakeFactory
import factory

from .models import User


fake = fakeFactory.create()


class UserFactory(factory.django.DjangoModelFactory):
    username = fake.user_name()
    email = fake.email()
    mobile_no = '0'
    password = fake.password()
    is_staff = True


class DisbursementUserFactory(UserFactory):
    class Meta:
        model = User
        abstract = False
