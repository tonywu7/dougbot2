# Generated by Django 3.2.7 on 2021-10-21 16:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0018_useraccess'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='useraccess',
            name='user',
        ),
        migrations.AddField(
            model_name='useraccess',
            name='user_id',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
