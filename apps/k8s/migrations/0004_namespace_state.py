# Generated by Django 5.0.7 on 2024-11-06 15:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('k8s', '0003_alter_pvc_size'),
    ]

    operations = [
        migrations.AddField(
            model_name='namespace',
            name='state',
            field=models.CharField(choices=[('creating', 'Resource is being created'), ('updating', 'Resource is being updated'), ('deleting', 'Resource is being deleted'), ('active', 'Resource is live'), ('stopped', 'Resource is stopped'), ('error', 'Resource is in error'), ('zombie', 'Resource exists in database but in cluster')], default='creating', max_length=16),
        ),
    ]
