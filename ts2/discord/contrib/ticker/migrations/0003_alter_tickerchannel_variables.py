# Generated by Django 3.2.5 on 2021-08-06 22:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ticker', '0002_auto_20210806_1524'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tickerchannel',
            name='variables',
            field=models.JSONField(),
        ),
    ]
