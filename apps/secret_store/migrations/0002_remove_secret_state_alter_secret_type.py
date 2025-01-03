# Generated by Django 5.0.7 on 2025-01-03 22:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('secret_store', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='secret',
            name='state',
        ),
        migrations.AlterField(
            model_name='secret',
            name='type',
            field=models.CharField(choices=[('opaque', 'Key value pair secrets'), ('dockerconfig', 'Docker config')], default='opaque', max_length=16),
        ),
    ]
