# Generated by Django 3.2.11 on 2022-01-31 15:37

from django.db import migrations, models

import dougbot2.models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DisabledApp",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("guild_id", models.IntegerField()),
                ("app_name", models.CharField(max_length=256)),
            ],
        ),
        migrations.CreateModel(
            name="Server",
            fields=[
                (
                    "snowflake",
                    models.BigIntegerField(
                        db_index=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="id",
                    ),
                ),
                ("name", models.TextField()),
                (
                    "prefix",
                    models.CharField(
                        default="d.",
                        max_length=16,
                        validators=[dougbot2.models.validate_prefix],
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=(dougbot2.models.NamingMixin, models.Model),
        ),
    ]