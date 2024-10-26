from django.db import models


class LBEndpoint(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    ip = models.CharField(max_length=100)
    port = models.CharField(max_length=100)
    protocol = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=30, default='Pending')

    class Meta:
        db_table = 'endpoints'
        ordering = ['-created_at']

