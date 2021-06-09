# Generated by Django 2.2.12 on 2020-12-22 10:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disbursement', '0007_banktransaction_is_single_step'),
    ]

    operations = [
        migrations.AlterField(
            model_name='banktransaction',
            name='status',
            field=models.CharField(choices=[('S', 'Successful'), ('R', 'Returned'), ('J', 'Rejected'), ('F', 'Failed'), ('P', 'Pending'), ('d', 'Default')], default='d', max_length=1, verbose_name='status'),
        ),
    ]
