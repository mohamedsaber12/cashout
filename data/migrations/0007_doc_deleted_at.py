# Generated by Django 2.2.12 on 2021-04-05 12:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0006_remove_doc_deleted'),
    ]

    operations = [
        migrations.AddField(
            model_name='doc',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
