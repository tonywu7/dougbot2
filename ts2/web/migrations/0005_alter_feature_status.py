# Generated by Django 3.2.5 on 2021-07-24 14:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0004_alter_feature_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feature',
            name='status',
            field=models.CharField(choices=[('PL', 'planned'), ('PR', 'drafting'), ('PS', 'partial'), ('RC', 'ready'), ('FN', 'finalized'), ('NO', 'never'), ('SP', 'speculative'), ('NA', 'no support'), ('RM', 'removed'), ('ST', 'abandoned')], max_length=32),
        ),
    ]