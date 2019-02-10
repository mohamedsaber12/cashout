from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings



class Format(models.Model):
    DISBURSEMENT = 1
    COLLECTION = 2
    TYPES = (
        (DISBURSEMENT, 'Disbursement'),
        (COLLECTION, 'Collection'),
    )
    identifier1 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name=_('Header 1'))
    identifier2 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name=_('Header 2'))
    identifier3 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name=_('Header 3'))
    identifier4 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name=_('Header 4'))
    identifier5 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name=_('Header 5'))
    identifier6 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name=_('Header 6'))
    identifier7 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name=_('Header 7'))
    identifier8 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name=_('Header 8'))
    identifier9 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name=_('Header 9'))
    identifier10 = models.CharField(
        max_length=128, null=True, blank=True, verbose_name=_('Header 10'))
    num_of_identifiers = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(10)],
                                             verbose_name=_('Number of identifiers filled'))

    hierarchy = models.PositiveSmallIntegerField()

    data_type = models.SmallIntegerField(choices=TYPES,default=1)

    name = models.CharField(max_length=128, unique=False)

    def identifiers(self):
        """return list of identifiers"""
        fields = []
        for field in self._meta.fields:
            if 'identifier' in field.name and getattr(self, field.name) and field.name != 'num_of_identifiers':
                fields.append(str(getattr(self, field.name)))
        return fields

 
    def headers_match(self,headers):
        identifiers = self.identifiers()
        return all(i in identifiers for i in headers if i)

    def validate_disbursement_unique(self):
        from data.models import FileCategory
        category = FileCategory.objects.filter(
            user_created__hierarchy=self.hierarchy).first()
        unique_field = category.unique_field
        if unique_field and unique_field not in self.identifiers():
            return False
        return True

    def validate_collection_unique(self):
        collection = CollectionData.objects.filter(
            user__hierarchy=self.hierarchy).first()
        unique_field = collection.unique_field
        unique_field2 = collection.unique_field2
        identifiers = self.identifiers()
        if unique_field2 and not all(i in identifiers for i in [unique_field, unique_field2]):
            return False
        if unique_field not in identifiers:
            return False
        return True

    def __str__(self):
        return self.name

    # TODO : POSTPONED not now
    def save(self, *args, **kwargs):
        """Add a permission for every file category"""
        self.num_of_identifiers = len(self.identifiers())
        super().save(*args, **kwargs)


class CollectionData(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.CASCADE, related_name='collection_data')
    has_partial_payment = models.BooleanField(default=0, verbose_name='Will there be partial payment?',
                                              help_text='If yes please mention the amount field below')
    can_overpay = models.BooleanField(default=0, verbose_name='This user accept over payment?')
    overflow_partial_acceptance_per_client = models.BooleanField(default=0,
                                                                 verbose_name='This biller accept over flow or partial per client?')
    unique_field = models.CharField(max_length=128,
                                    verbose_name='What is the unique field?')
    unique_field2 = models.CharField(max_length=128, blank=True,
                                     verbose_name='What is the unique field?')
    total_amount_field = models.CharField(max_length=128, blank=True,
                                    verbose_name='what is total of loan amount field?',
                                    help_text='for ex: loan_field')
    payable_amount_field = models.CharField(max_length=128,
                                            verbose_name='what is paid amount field?',
                                            help_text='For ex: Installment field')
    date_field = models.CharField(max_length=128,
                                  verbose_name='what is date field?',
                                  help_text='Don\'t write number of identifier, write the field itself')
    mobile_field = models.CharField(max_length=128, null=True, blank=True,
                                    verbose_name='what is Phone number field?',
                                    help_text='For ex: mobile_no, it can be one of the unique fields')
