# Generated by Django 3.2.5 on 2021-07-24 23:24

from django.db import migrations
import ts2.discord.models


class Migration(migrations.Migration):

    dependencies = [
        ('discord', '0016_auto_20210724_1428'),
    ]

    operations = [
        migrations.AlterField(
            model_name='server',
            name='readable',
            field=ts2.discord.models.PermissionField(default=(), verbose_name='readable perms'),
        ),
        migrations.AlterField(
            model_name='server',
            name='writable',
            field=ts2.discord.models.PermissionField(default=(), verbose_name='writable perms'),
        ),
    ]
