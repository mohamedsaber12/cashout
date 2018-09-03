from __future__ import unicode_literals

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

# Create your models here.


class FileCategory(models.Model):
    file_type = models.CharField(max_length=128, unique=False, verbose_name='File Category Name')
    identifier1 = models.CharField(max_length=128, null=True, blank=True, verbose_name='Indentifier')
    identifier2 = models.CharField(max_length=128, null=True, blank=True, verbose_name='Indentifier')
    identifier3 = models.CharField(max_length=128, null=True, blank=True, verbose_name='Indentifier')
    identifier4 = models.CharField(max_length=128, null=True, blank=True, verbose_name='Indentifier')
    identifier5 = models.CharField(max_length=128, null=True, blank=True, verbose_name='Indentifier')
    identifier6 = models.CharField(max_length=128, null=True, blank=True, verbose_name='Indentifier')
    identifier7 = models.CharField(max_length=128, null=True, blank=True, verbose_name='Indentifier')
    identifier8 = models.CharField(max_length=128, null=True, blank=True, verbose_name='Indentifier')
    identifier9 = models.CharField(max_length=128, null=True, blank=True, verbose_name='Indentifier')
    identifier10 = models.CharField(max_length=128, null=True, blank=True, verbose_name='Indentifier')
    num_of_identifiers = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(10)],
                                             verbose_name='Number of identifiers filled')
    user_created = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.CASCADE)
    is_processed = models.BooleanField(default=True, verbose_name='will the data uploaded be processed?')
    has_header = models.BooleanField(default=True, verbose_name='Will the data uploaded have header?')
    unique_field = models.CharField(max_length=128, null=True, blank=True,
                                    verbose_name='What is the unique field?')
    amount_field = models.CharField(max_length=128, null=True, blank=True,
                                    verbose_name='what is amount field?',
                                    help_text='for ex: loan_field')

    class Meta:
        verbose_name_plural = 'File Categories'
        unique_together = (('user_created', 'file_type'),)

    def __unicode__(self):
        return self.user_created.username + ' ' + self.file_type

    def __str__(self):
        return self.user_created.username + ' ' + self.file_type

    @property
    def processed(self):
        return self.is_processed

    def identifiers(self):
        fields = []
        for field in self._meta.fields:
            if 'identifier' in field.name:
                if getattr(self, field.name) == '' or field.name == 'num_of_identifiers':
                    continue
                fields.append(str(getattr(self, field.name)))
        for _ in range(len(fields)):
            try:
                fields.remove('None')
            except:
                break
        return fields

    # TODO : POSTPONED not now
    def save(self, *args, **kwargs):
        """Add a permission for every file category"""
        # Permission.objects.get_or_create(content_type=ContentType.objects.get_for_model(Doc),
        #                                  codename="access_type_%s" % self.file_type,
        #                                  name="access type %s" % self.file_type)

        self.num_of_identifiers = len(self.identifiers())
        super(FileCategory, self).save(*args, **kwargs)
