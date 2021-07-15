# Generated by Django 3.2.5 on 2021-07-15 00:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('acl', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='accesscontrol',
            name='commands',
        ),
        migrations.AddField(
            model_name='accesscontrol',
            name='command',
            field=models.CharField(default='', max_length=120),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='accesscontrol',
            name='error',
            field=models.TextField(blank=True),
        ),
        migrations.AddIndex(
            model_name='accesscontrol',
            index=models.Index(fields=['server_id', 'command'], name='idx_acl_server_id_command'),
        ),
    ]
