# Generated by Django 5.0.7 on 2024-12-30 21:07

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('container_registry', '0001_initial'),
        ('k8s', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='containerregistry',
            name='namespace',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='registries', to='k8s.namespace'),
        ),
        migrations.AddField(
            model_name='registrywebhook',
            name='registry',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='webhooks', to='container_registry.containerregistry'),
        ),
        migrations.AddField(
            model_name='repotoken',
            name='registry',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tokens', to='container_registry.containerregistry'),
        ),
    ]
