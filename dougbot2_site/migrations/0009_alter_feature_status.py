# Generated by Django 3.2.5 on 2021-07-24 16:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0008_alter_feature_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feature',
            name='status',
            field=models.CharField(choices=[('01-PL', 'planned'), ('02-PR', 'drafting'), ('03-PS', 'partial'), ('04-RC', 'ready'), ('05-FN', 'frozen'), ('10-SU', 'superseded'), ('20-SP', 'speculative'), ('30-NO', 'never'), ('31-NA', 'no support'), ('32-RM', 'removed'), ('33-ST', 'abandoned')], max_length=32),
        ),
    ]