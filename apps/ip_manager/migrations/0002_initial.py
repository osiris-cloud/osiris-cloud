# Generated by Django 5.0.7 on 2024-10-04 22:01

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('ip_manager', '0001_initial'),
        ('vm', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ipv4',
            name='vm',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='vm.vm'),
        ),
    ]
