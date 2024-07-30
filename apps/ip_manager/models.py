from django.db import models

from ..users.models import User


class IPv4(models.Model):
    address = models.GenericIPAddressField(protocol='IPv4')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ipv4s')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.address

    class Meta:
        db_table = 'ipv4'
        verbose_name = 'IPv4'
        verbose_name_plural = 'IPv4s'


class IPv6(models.Model):
    address = models.GenericIPAddressField(protocol='IPv6')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ipv6s')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.address

    class Meta:
        db_table = 'ipv6'
        verbose_name = 'IPv6'
        verbose_name_plural = 'IPv6s'
