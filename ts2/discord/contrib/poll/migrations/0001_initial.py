# Generated by Django 3.2.5 on 2021-08-10 16:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('discord', '0020_auto_20210730_1553'),
    ]

    operations = [
        migrations.CreateModel(
            name='SuggestionChannel',
            fields=[
                ('channel', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='+', serialize=False, to='discord.channel')),
                ('description', models.TextField(blank=True)),
                ('upvote', models.CharField(default='🔼', max_length=512)),
                ('downvote', models.CharField(default='🔽', max_length=512)),
                ('approve', models.CharField(default='✅', max_length=512)),
                ('reject', models.CharField(default='🚫', max_length=512)),
                ('requires_text', models.BooleanField(default=True)),
                ('requires_uploads', models.IntegerField(default=0)),
                ('requires_links', models.IntegerField(default=0)),
                ('server', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='discord.server')),
            ],
        ),
    ]