# Generated by Django 5.0.7 on 2024-12-30 21:07

import core.model_fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Container',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('containerid', core.model_fields.UUID7StringField(auto_created=True, default=core.model_fields.generate_uuid7, max_length=36, unique=True)),
                ('type', models.CharField(choices=[('init', 'Init Container'), ('main', 'Main Container'), ('sidecar', 'Sidecar Container')], max_length=16)),
                ('image', models.TextField()),
                ('port', models.IntegerField(default=None, null=True)),
                ('port_protocol', models.CharField(choices=[('tcp', 'TCP'), ('udp', 'UDP')], default=None, max_length=16, null=True)),
                ('command', models.JSONField(default=list, null=True)),
                ('args', models.JSONField(default=list, null=True)),
                ('cpu_request', models.FloatField()),
                ('memory_request', models.IntegerField()),
                ('cpu_limit', models.IntegerField()),
                ('memory_limit', models.FloatField()),
            ],
        ),
        migrations.CreateModel(
            name='ContainerApp',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('appid', core.model_fields.UUID7StringField(auto_created=True, default=core.model_fields.generate_uuid7, max_length=36, unique=True)),
                ('name', models.CharField(max_length=64)),
                ('slug', models.CharField(max_length=64)),
                ('replicas', models.IntegerField(default=1)),
                ('connection_port', models.IntegerField(default=None, null=True)),
                ('connection_protocol', models.CharField(choices=[('http', 'Web app'), ('tcp', 'TCP on random port'), ('udp', 'UDP on random port')], max_length=16)),
                ('restart_policy', models.CharField(choices=[('always', 'Always'), ('on_failure', 'On Failure'), ('never', 'Never')], default='always', max_length=16)),
                ('state', models.CharField(choices=[('creating', 'Resource is being created'), ('updating', 'Resource is being updated'), ('deleting', 'Resource is being deleted'), ('active', 'Resource is live'), ('stopped', 'Resource is stopped'), ('error', 'Resource is in error'), ('zombie', 'Resource exists in database but in cluster'), ('orphan', 'Resource exists in cluster but not in database')], default='creating', max_length=16)),
                ('exposed_public', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='CustomDomain',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=253)),
                ('gen_tls_cert', models.BooleanField()),
            ],
        ),
        migrations.CreateModel(
            name='HPA',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enable', models.BooleanField(default=False)),
                ('min_replicas', models.IntegerField(default=1)),
                ('max_replicas', models.IntegerField(default=1)),
                ('scaleup_stb_window', models.IntegerField(default=300)),
                ('scaledown_stb_window', models.IntegerField(default=300)),
                ('cpu_trigger', models.IntegerField(default=90, null=True)),
                ('memory_trigger', models.IntegerField(default=90, null=True)),
            ],
        ),
    ]
