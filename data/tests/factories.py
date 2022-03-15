import factory
import factory.django

from data.models import FileCategory
from users.tests.factories import AdminUserFactory
from users.models import User
from faker import Factory
from data.models.doc import Doc
from data.models.category_data import Format
from data.models.file_data import FileData
import uuid


fake = Factory.create()


class DisbursementFileCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FileCategory

    user_created = factory.SubFactory(AdminUserFactory)
    name = 'test'
    unique_field = 'MSISDN'
    amount_field = 'Amount'
    issuer_field = 'Issuer'
    no_of_reviews_required = 1
    
    
class FormarFactory(factory.DjangoModelFactory):
    class Meta:
        model = Format
        
    identifier1 = factory.LazyFunction(fake.first_name)
    identifier2 = factory.LazyFunction(fake.first_name)
    identifier3 = factory.LazyFunction(fake.first_name)
    identifier4 = factory.LazyFunction(fake.first_name)
    identifier5 = factory.LazyFunction(fake.first_name)
    identifier6 = factory.LazyFunction(fake.first_name)
    identifier7 = factory.LazyFunction(fake.first_name)
    identifier8 = factory.LazyFunction(fake.first_name)
    identifier9 = factory.LazyFunction(fake.first_name)
    identifier10 = factory.LazyFunction(fake.first_name)
    num_of_identifiers = 10
    name = factory.LazyFunction(fake.first_name)
    hierarchy = 2
    
class FileDataFactory(factory.DjangoModelFactory):
    class Meta:
        model = FileData
        
    data = {"test": "test"}
    date = "2020-01-01"
    is_draft = False
    is_downloaded = True
    has_full_payment = True
    
    
class DocFactory(factory.DjangoModelFactory):
    
    class Meta:
        model = Doc
        
    is_disbursed = True
    can_be_disbursed = True
    is_processed = True
    processing_failure_reason = fake.first_name
    total_amount = 100
    total_amount_with_fees_vat = 120
    total_count = 10
    has_change_profile_callback = True
    format = factory.SubFactory(FormarFactory)
    # file = factory.django.ImageField(from_file='test.png', color='blue',content_type="image/png")
    
