# Generated by Django 5.0.7 on 2024-12-30 21:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='accesstoken',
            name='system_use',
        ),
        migrations.AddField(
            model_name='accesstoken',
            name='attributes',
            field=models.JSONField(default=dict),
        ),
    ]
