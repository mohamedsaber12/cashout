from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Format(models.Model):
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
    category = models.ForeignKey(
        'data.FileCategory', blank=True, null=True, on_delete=models.CASCADE, related_name='file_category')

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
        self.num_of_identifiers = len(self.identifiers())
        super().save(*args, **kwargs)