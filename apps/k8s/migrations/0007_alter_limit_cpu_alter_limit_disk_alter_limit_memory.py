# Generated by Django 5.0.7 on 2024-07-24 18:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('k8s', '0006_alter_namespaces_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='limit',
            name='cpu',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='limit',
            name='disk',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='limit',
            name='memory',
            field=models.IntegerField(default=0),
        ),
    ]
