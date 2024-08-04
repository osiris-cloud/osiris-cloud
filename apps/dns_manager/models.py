from django.db import models

from ..users.models import User


class Record(models.Model):
    key = models.CharField(max_length=256)
    value = models.CharField()
    ttl = models.PositiveIntegerField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dns_records')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dns_records'
