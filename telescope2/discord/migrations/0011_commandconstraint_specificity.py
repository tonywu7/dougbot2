# Generated by Django 3.2.4 on 2021-06-16 10:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('discord', '0010_alter_commandconstraint_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='commandconstraint',
            name='specificity',
            field=models.IntegerField(default=0),
        ),
    ]
