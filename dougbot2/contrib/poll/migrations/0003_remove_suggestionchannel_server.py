# Generated by Django 3.2.5 on 2021-08-11 11:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('poll', '0002_suggestionchannel_keyword'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='suggestionchannel',
            name='server',
        ),
    ]