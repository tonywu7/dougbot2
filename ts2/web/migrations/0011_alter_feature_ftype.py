# Generated by Django 3.2.5 on 2021-07-24 16:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0010_alter_feature_ftype'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feature',
            name='ftype',
            field=models.CharField(choices=[('infrastructure', 'infrastructure'), ('command', 'command'), ('system', 'system'), ('integration', 'integration'), ('qol', 'quality of life'), ('doc', 'documentation'), ('web', 'website'), ('special', 'special')], max_length=32),
        ),
    ]