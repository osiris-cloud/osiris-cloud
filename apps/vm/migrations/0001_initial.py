# Generated by Django 5.0.7 on 2024-07-18 05:55

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('k8s', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='VM',
            fields=[
                ('vmid', models.UUIDField(auto_created=True, default=uuid.uuid4, unique=True)),
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('k8s_name', models.CharField(max_length=100)),
                ('cpu', models.IntegerField()),
                ('memory', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(default='Pending', max_length=30)),
                ('disk', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vms', to='k8s.pvc')),
                ('namespace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='k8s.namespace')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vms', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
