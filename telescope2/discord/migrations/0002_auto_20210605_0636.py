# Generated by Django 3.2.4 on 2021-06-05 13:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('discord', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel('BotPrefs', 'GuildPreference'),
    ]
