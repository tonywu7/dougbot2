# Generated by Django 3.2.7 on 2021-11-30 15:04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rolemenu", "0002_auto_20211130_0648"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="rolecounter",
            name="rolemenu_ro_channel_527488_idx",
        ),
        migrations.RemoveField(
            model_name="rolecounter",
            name="channel_id",
        ),
        migrations.RemoveField(
            model_name="rolecounter",
            name="message_id",
        ),
        migrations.AddField(
            model_name="rolecounter",
            name="menu",
            field=models.ForeignKey(
                default=0,
                on_delete=django.db.models.deletion.CASCADE,
                to="rolemenu.rolestatistics",
            ),
            preserve_default=False,
        ),
    ]
