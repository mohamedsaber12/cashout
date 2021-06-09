# Generated by Django 2.2.12 on 2020-11-18 11:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disbursement', '0004_banktransaction_document'),
    ]

    operations = [
        migrations.AddField(
            model_name='banktransaction',
            name='is_single_step',
            field=models.BooleanField(default=False, verbose_name='Is manual patch single step transaction?'),
        ),
    ]
