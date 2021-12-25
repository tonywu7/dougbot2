# Generated by Django 3.2.4 on 2021-06-22 14:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('discord', '0001_discord_models'),
    ]

    operations = [
        migrations.AlterField(
            model_name='commandconstraint',
            name='collection',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='constraints', to='discord.commandconstraintlist'),
        ),
        migrations.AlterField(
            model_name='commandconstraint',
            name='type',
            field=models.IntegerField(choices=[(0, 'None'), (1, 'Any'), (2, 'All')]),
        ),
        migrations.AlterField(
            model_name='server',
            name='name',
            field=models.TextField(),
        ),
    ]