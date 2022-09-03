# Generated by Django 3.2.7 on 2021-11-30 14:29

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="RoleCounter",
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
                ("role_id", models.BigIntegerField()),
                ("channel_id", models.BigIntegerField()),
                ("message_id", models.BigIntegerField()),
                ("emote", models.CharField(max_length=256)),
                ("description", models.TextField()),
            ],
        ),
        migrations.AddIndex(
            model_name="rolecounter",
            index=models.Index(
                fields=["role_id"], name="rolemenu_ro_role_id_45721a_idx"
            ),
        ),
    ]