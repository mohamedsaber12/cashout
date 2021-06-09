# Generated by Django 2.2.12 on 2020-11-23 10:27

from decimal import Decimal
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('utilities', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='feesetup',
            name='max_value',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, help_text='Fees value to be added instead of the fixed/percentage fees when the total calculated fees before 14% is greater than this max value', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0')), django.core.validators.MaxValueValidator(Decimal('10000.0'))], verbose_name='Maximum value'),
        ),
        migrations.AddField(
            model_name='feesetup',
            name='min_value',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, help_text='Fees value to be added instead of the fixed/percentage fees when the total calculated fees before 14% is less than this min value', max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0')), django.core.validators.MaxValueValidator(Decimal('100.0'))], verbose_name='Minimum value'),
        ),
    ]
