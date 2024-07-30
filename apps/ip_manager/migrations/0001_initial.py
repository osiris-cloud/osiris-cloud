# Generated by Django 5.0.7 on 2024-07-18 05:55

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='IPv4',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.GenericIPAddressField(protocol='IPv4')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'IPv4',
                'verbose_name_plural': 'IPv4s',
                'db_table': 'ipv4',
            },
        ),
        migrations.CreateModel(
            name='IPv6',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.GenericIPAddressField(protocol='IPv6')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'IPv6',
                'verbose_name_plural': 'IPv6s',
                'db_table': 'ipv6',
            },
        ),
    ]