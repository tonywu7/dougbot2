# Generated by Django 3.2.5 on 2021-08-10 23:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('poll', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='suggestionchannel',
            name='keyword',
            field=models.CharField(default='', max_length=64),
            preserve_default=False,
        ),
    ]