# Generated by Django 5.1.5 on 2025-03-20 01:21

import core.model_fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AccessToken',
            fields=[
                ('keyid', core.model_fields.UUID7StringField(default=core.model_fields.generate_uuid7, max_length=36, primary_key=True, serialize=False, unique=True)),
                ('key', models.CharField(max_length=40, unique=True)),
                ('name', models.CharField(blank=True, max_length=64)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_used', models.DateTimeField(blank=True, null=True)),
                ('scopes', models.JSONField(default=list)),
                ('can_write', models.BooleanField(default=False)),
                ('expiration', models.DateTimeField(default=None, null=True)),
                ('attributes', models.JSONField(default=dict)),
            ],
        ),
    ]
