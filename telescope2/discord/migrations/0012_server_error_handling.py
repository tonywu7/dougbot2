# Generated by Django 3.2.4 on 2021-06-16 13:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('discord', '0011_commandconstraint_specificity'),
    ]

    operations = [
        migrations.AddField(
            model_name='server',
            name='error_handling',
            field=models.JSONField(default=dict, verbose_name='error handling config'),
        ),
    ]