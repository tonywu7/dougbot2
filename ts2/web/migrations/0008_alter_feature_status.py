# Generated by Django 3.2.5 on 2021-07-24 15:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0007_alter_feature_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feature',
            name='status',
            field=models.CharField(choices=[('01-SP', 'speculative'), ('02-PL', 'planned'), ('03-PR', 'drafting'), ('04-PS', 'partial'), ('05-RC', 'ready'), ('06-SU', 'superseded'), ('07-FN', 'frozen'), ('08-NO', 'never'), ('09-NA', 'no support'), ('10-RM', 'removed'), ('11-ST', 'abandoned')], max_length=32),
        ),
    ]
