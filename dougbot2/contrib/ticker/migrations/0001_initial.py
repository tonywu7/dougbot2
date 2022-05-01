# Generated by Django 3.2.11 on 2022-01-31 15:37

import arrow.api
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TickerChannel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel_id', models.BigIntegerField()),
                ('content', models.TextField()),
                ('variables', models.JSONField(default=dict)),
                ('created', models.DateTimeField(default=arrow.api.utcnow)),
                ('refresh', models.FloatField()),
                ('expire', models.DateTimeField(null=True)),
                ('parent_id', models.BigIntegerField()),
                ('placement', models.JSONField(default=dict)),
            ],
        ),
    ]
