# Generated by Django 2.2.12 on 2020-11-09 17:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0002_auto_20201109_1918'),
        ('disbursement', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='banktransaction',
            name='document',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='bank_transactions', to='data.Doc', verbose_name='Disbursement Document'),
        ),
        migrations.AlterField(
            model_name='banktransaction',
            name='transaction_status_code',
            field=models.CharField(blank=True, max_length=6, null=True, verbose_name='Transaction Status Code'),
        ),
    ]
