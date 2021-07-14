# Generated by Django 3.2.5 on 2021-07-12 01:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('discord', '0009_alter_user_timezone'),
        ('internet', '0004_alter_roletimezone_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='roletimezone',
            name='role',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='discord.role'),
        ),
    ]