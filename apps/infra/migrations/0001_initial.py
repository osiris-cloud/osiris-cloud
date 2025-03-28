# Generated by Django 5.1.5 on 2025-03-20 01:21

import core.model_fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Namespace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nsid', models.CharField(max_length=20, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('locked', models.BooleanField(default=False)),
                ('state', models.CharField(choices=[('creating', 'Resource is being created'), ('updating', 'Resource is being updated'), ('deleting', 'Resource is being deleted'), ('created', 'Resource is created'), ('active', 'Resource is live'), ('stopped', 'Resource is stopped'), ('error', 'Resource is in error'), ('zombie', 'Resource exists in database but in cluster'), ('orphan', 'Resource exists in cluster but not in database')], default='creating', max_length=16)),
            ],
            options={
                'db_table': 'namespaces',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Volume',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('volid', core.model_fields.UUID7StringField(auto_created=True, default=core.model_fields.generate_uuid7, max_length=36, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('type', models.CharField(choices=[('temp', 'Temporary Storage'), ('fs', 'File System'), ('block', 'Block Device'), ('secret', 'Secret')], max_length=16)),
                ('size', models.FloatField()),
                ('mount_path', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('metadata', models.JSONField(default=dict)),
            ],
            options={
                'db_table': 'volumes',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('eventid', core.model_fields.UUID7StringField(auto_created=True, default=core.model_fields.generate_uuid7, max_length=36, unique=True)),
                ('message', models.TextField()),
                ('related_link', models.CharField(blank=True, max_length=256, null=True)),
                ('time', models.DateTimeField(auto_now_add=True)),
                ('read', models.BooleanField(default=False)),
                ('namespace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='infra.namespace')),
            ],
            options={
                'db_table': 'ns_events',
            },
        ),
        migrations.CreateModel(
            name='NamespaceRoles',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('owner', 'Owner: Full control'), ('manager', 'Manager: Read and write'), ('viewer', 'Viewer: Read only')], default='viewer', max_length=10)),
                ('namespace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='infra.namespace')),
            ],
            options={
                'db_table': 'namespace_roles',
            },
        ),
    ]
