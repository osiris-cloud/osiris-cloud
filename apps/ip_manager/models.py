from django.db import models

from ..users.models import User


class IPv4(models.Model):
    address = models.GenericIPAddressField(protocol='IPv4')
    mac = models.CharField(max_length=17, null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ipv4s')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ipv4'
