# Generated by Django 3.2.5 on 2021-07-24 21:28

from django.db import migrations
import ts2.discord.models


class Migration(migrations.Migration):

    dependencies = [
        ('discord', '0015_rename_parent_channel_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='server',
            name='readable',
            field=ts2.discord.models.PermissionField(default=0, verbose_name='readable perms'),
        ),
        migrations.AddField(
            model_name='server',
            name='writable',
            field=ts2.discord.models.PermissionField(default=0, verbose_name='writable perms'),
        ),
    ]